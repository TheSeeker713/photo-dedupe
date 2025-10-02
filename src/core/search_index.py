from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Set, Any
import logging

# Import local modules with fallback
try:
    from app.settings import Settings
except ImportError:
    try:
        from ..app.settings import Settings
    except ImportError:
        Settings = None

# Configure logging
logger = logging.getLogger(__name__)


class BKTreeNode:
    """Node in a BK-tree for approximate string matching."""
    
    def __init__(self, hash_value: str, file_id: int):
        self.hash_value = hash_value
        self.file_id = file_id
        self.children: Dict[int, BKTreeNode] = {}
    
    def add(self, hash_value: str, file_id: int) -> None:
        """Add a hash to the BK-tree."""
        distance = hamming_distance(self.hash_value, hash_value)
        
        if distance in self.children:
            self.children[distance].add(hash_value, file_id)
        else:
            self.children[distance] = BKTreeNode(hash_value, file_id)
    
    def search(self, target_hash: str, max_distance: int) -> List[Tuple[int, int]]:
        """Search for hashes within max_distance of target_hash."""
        results = []
        distance = hamming_distance(self.hash_value, target_hash)
        
        if distance <= max_distance:
            results.append((self.file_id, distance))
        
        # Search children within the triangle inequality bounds
        for child_distance, child_node in self.children.items():
            if abs(distance - child_distance) <= max_distance:
                results.extend(child_node.search(target_hash, max_distance))
        
        return results


class BKTree:
    """BK-tree for efficient approximate hash matching."""
    
    def __init__(self):
        self.root: Optional[BKTreeNode] = None
        self.size = 0
    
    def add(self, hash_value: str, file_id: int) -> None:
        """Add a hash to the tree."""
        if not hash_value:
            return
        
        if self.root is None:
            self.root = BKTreeNode(hash_value, file_id)
        else:
            self.root.add(hash_value, file_id)
        
        self.size += 1
    
    def search(self, target_hash: str, max_distance: int) -> List[Tuple[int, int]]:
        """Search for hashes within max_distance of target_hash."""
        if not target_hash or self.root is None:
            return []
        
        return self.root.search(target_hash, max_distance)
    
    def is_empty(self) -> bool:
        """Check if the tree is empty."""
        return self.root is None


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return float('inf')
    
    try:
        # Convert hex strings to integers and compute XOR
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        
        # Count set bits in XOR (Hamming distance)
        return bin(val1 ^ val2).count('1')
    
    except ValueError:
        return float('inf')


class NearDuplicateSearchIndex:
    """Near-duplicate search index using BK-trees for efficient approximate matching."""
    
    # Distance thresholds by performance preset
    DISTANCE_THRESHOLDS = {
        "Ultra-Lite": 6,   # Stricter threshold for low-end
        "Balanced": 8,     # Moderate threshold
        "Accurate": 12,    # Relaxed threshold for better recall
    }
    
    def __init__(self, db_path: Path, settings):
        """Initialize near-duplicate search index."""
        self.db_path = db_path
        self.settings = settings
        
        # Get current performance preset
        perf_config = settings._data.get("Performance", {})
        self.current_preset = perf_config.get("current_preset", "Balanced")
        self.max_distance = self.DISTANCE_THRESHOLDS[self.current_preset]
        
        # BK-trees for different hash types
        self.phash_tree = BKTree()
        self.dhash_tree = BKTree()
        self.whash_tree = BKTree()
        
        # Cache for file information
        self._file_cache: Dict[int, Dict[str, Any]] = {}
        
        # Index statistics
        self.last_built = None
        self.index_version = 1
        
        logger.info(f"NearDuplicateSearchIndex initialized: preset={self.current_preset}, "
                   f"max_distance={self.max_distance}")
    
    def build_index(self, progress_callback=None) -> int:
        """Build BK-tree indexes from database features."""
        logger.info("Building near-duplicate search index...")
        start_time = time.time()
        
        # Clear existing trees
        self.phash_tree = BKTree()
        self.dhash_tree = BKTree()
        self.whash_tree = BKTree()
        self._file_cache.clear()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all files with features
                cursor = conn.execute("""
                    SELECT f.id, f.path, f.size, feat.phash, feat.dhash, feat.whash
                    FROM files f
                    JOIN features feat ON f.id = feat.file_id
                    WHERE feat.phash IS NOT NULL
                    ORDER BY f.id
                """)
                
                records = cursor.fetchall()
                total_records = len(records)
                
                logger.info(f"Processing {total_records} files with features")
                
                for i, (file_id, file_path, file_size, phash, dhash, whash) in enumerate(records):
                    # Add to BK-trees
                    if phash:
                        self.phash_tree.add(phash, file_id)
                    
                    if dhash:
                        self.dhash_tree.add(dhash, file_id)
                    
                    if whash:
                        self.whash_tree.add(whash, file_id)
                    
                    # Cache file information
                    self._file_cache[file_id] = {
                        'path': file_path,
                        'size': file_size,
                        'phash': phash,
                        'dhash': dhash,
                        'whash': whash
                    }
                    
                    # Progress callback
                    if progress_callback and (i + 1) % 100 == 0:
                        progress_callback(i + 1, total_records)
                
                self.last_built = time.time()
                build_time = self.last_built - start_time
                
                logger.info(f"Index built successfully in {build_time:.2f}s: "
                           f"pHash={self.phash_tree.size}, "
                           f"dHash={self.dhash_tree.size}, "
                           f"wHash={self.whash_tree.size}")
                
                return total_records
        
        except sqlite3.Error as e:
            logger.error(f"Failed to build index: {e}")
            return 0
    
    def find_near_duplicates(self, file_id: int, max_distance: Optional[int] = None) -> List[Dict[str, Any]]:
        """Find near-duplicate candidates for a given file."""
        if max_distance is None:
            max_distance = self.max_distance
        
        # Get file information and hashes
        file_info = self._get_file_info(file_id)
        if not file_info:
            logger.warning(f"File ID {file_id} not found in index")
            return []
        
        phash = file_info.get('phash')
        dhash = file_info.get('dhash')
        whash = file_info.get('whash')
        
        if not phash:
            logger.warning(f"No pHash available for file ID {file_id}")
            return []
        
        logger.debug(f"Searching for near-duplicates of file {file_id} "
                    f"within distance {max_distance}")
        
        # Search all available hash types
        candidates = {}  # file_id -> candidate info
        
        # Search pHash tree (primary)
        phash_results = self.phash_tree.search(phash, max_distance)
        for candidate_id, distance in phash_results:
            if candidate_id != file_id:  # Exclude self
                if candidate_id not in candidates:
                    candidates[candidate_id] = {
                        'file_id': candidate_id,
                        'distances': {},
                        'min_distance': distance
                    }
                candidates[candidate_id]['distances']['phash'] = distance
                candidates[candidate_id]['min_distance'] = min(
                    candidates[candidate_id]['min_distance'], distance
                )
        
        # Search dHash tree if available
        if dhash and not self.dhash_tree.is_empty():
            dhash_results = self.dhash_tree.search(dhash, max_distance)
            for candidate_id, distance in dhash_results:
                if candidate_id != file_id:
                    if candidate_id not in candidates:
                        candidates[candidate_id] = {
                            'file_id': candidate_id,
                            'distances': {},
                            'min_distance': distance
                        }
                    candidates[candidate_id]['distances']['dhash'] = distance
                    candidates[candidate_id]['min_distance'] = min(
                        candidates[candidate_id]['min_distance'], distance
                    )
        
        # Search wHash tree if available
        if whash and not self.whash_tree.is_empty():
            whash_results = self.whash_tree.search(whash, max_distance)
            for candidate_id, distance in whash_results:
                if candidate_id != file_id:
                    if candidate_id not in candidates:
                        candidates[candidate_id] = {
                            'file_id': candidate_id,
                            'distances': {},
                            'min_distance': distance
                        }
                    candidates[candidate_id]['distances']['whash'] = distance
                    candidates[candidate_id]['min_distance'] = min(
                        candidates[candidate_id]['min_distance'], distance
                    )
        
        # Enrich candidates with file information
        enriched_candidates = []
        for candidate_info in candidates.values():
            candidate_id = candidate_info['file_id']
            candidate_file_info = self._get_file_info(candidate_id)
            
            if candidate_file_info:
                enriched_info = {
                    'file_id': candidate_id,
                    'file_path': candidate_file_info['path'],
                    'file_size': candidate_file_info['size'],
                    'distances': candidate_info['distances'],
                    'min_distance': candidate_info['min_distance'],
                    'similarity_score': self._calculate_similarity_score(candidate_info['distances'])
                }
                enriched_candidates.append(enriched_info)
        
        # Sort by minimum distance (best matches first)
        enriched_candidates.sort(key=lambda x: x['min_distance'])
        
        logger.debug(f"Found {len(enriched_candidates)} near-duplicate candidates "
                    f"for file {file_id}")
        
        return enriched_candidates
    
    def find_near_duplicates_batch(self, file_ids: List[int], 
                                 max_distance: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """Find near-duplicates for multiple files efficiently."""
        results = {}
        
        for file_id in file_ids:
            results[file_id] = self.find_near_duplicates(file_id, max_distance)
        
        return results
    
    def find_similar_by_hash(self, target_hash: str, hash_type: str = 'phash', 
                           max_distance: Optional[int] = None) -> List[Dict[str, Any]]:
        """Find files similar to a given hash value."""
        if max_distance is None:
            max_distance = self.max_distance
        
        # Select appropriate tree
        if hash_type == 'phash':
            tree = self.phash_tree
        elif hash_type == 'dhash':
            tree = self.dhash_tree
        elif hash_type == 'whash':
            tree = self.whash_tree
        else:
            logger.error(f"Unknown hash type: {hash_type}")
            return []
        
        if tree.is_empty():
            return []
        
        # Search the tree
        results = tree.search(target_hash, max_distance)
        
        # Enrich with file information
        enriched_results = []
        for file_id, distance in results:
            file_info = self._get_file_info(file_id)
            if file_info:
                enriched_info = {
                    'file_id': file_id,
                    'file_path': file_info['path'],
                    'file_size': file_info['size'],
                    'distance': distance,
                    'hash_type': hash_type
                }
                enriched_results.append(enriched_info)
        
        # Sort by distance
        enriched_results.sort(key=lambda x: x['distance'])
        
        return enriched_results
    
    def _get_file_info(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Get cached file information or fetch from database."""
        if file_id in self._file_cache:
            return self._file_cache[file_id]
        
        # Fetch from database if not cached
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT f.path, f.size, feat.phash, feat.dhash, feat.whash
                    FROM files f
                    LEFT JOIN features feat ON f.id = feat.file_id
                    WHERE f.id = ?
                """, (file_id,))
                
                result = cursor.fetchone()
                if result:
                    file_info = {
                        'path': result[0],
                        'size': result[1],
                        'phash': result[2],
                        'dhash': result[3],
                        'whash': result[4]
                    }
                    self._file_cache[file_id] = file_info
                    return file_info
        
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch file info for {file_id}: {e}")
        
        return None
    
    def _calculate_similarity_score(self, distances: Dict[str, int]) -> float:
        """Calculate a composite similarity score from multiple hash distances."""
        if not distances:
            return 0.0
        
        # Weight different hash types
        weights = {
            'phash': 0.5,   # Primary perceptual hash
            'dhash': 0.3,   # Difference hash
            'whash': 0.2    # Wavelet hash
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for hash_type, distance in distances.items():
            if hash_type in weights:
                # Convert distance to similarity (lower distance = higher similarity)
                # Using exponential decay: similarity = e^(-distance/8)
                similarity = 2 ** (-distance / 8.0)
                total_score += weights[hash_type] * similarity
                total_weight += weights[hash_type]
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the search index."""
        return {
            'last_built': self.last_built,
            'index_version': self.index_version,
            'current_preset': self.current_preset,
            'max_distance': self.max_distance,
            'phash_tree_size': self.phash_tree.size,
            'dhash_tree_size': self.dhash_tree.size,
            'whash_tree_size': self.whash_tree.size,
            'total_files_indexed': len(self._file_cache),
            'distance_thresholds': self.DISTANCE_THRESHOLDS
        }
    
    def is_index_built(self) -> bool:
        """Check if index has been built."""
        return self.last_built is not None and not self.phash_tree.is_empty()
    
    def clear_index(self) -> None:
        """Clear the search index."""
        self.phash_tree = BKTree()
        self.dhash_tree = BKTree()
        self.whash_tree = BKTree()
        self._file_cache.clear()
        self.last_built = None
        logger.info("Search index cleared")
    
    def rebuild_if_needed(self, force: bool = False) -> bool:
        """Rebuild index if needed or forced."""
        if force or not self.is_index_built():
            return self.build_index() > 0
        return True