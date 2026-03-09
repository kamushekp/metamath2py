from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

@dataclass
class SearchResult:
    path: str
    score: float
    category: str
    line_count: int
    snippet: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

class SimpleSearchClient:
    """
    A simple file-based search client that scans the dataset directory for matches.
    Used as fallback when OpenSearch is unavailable.
    """
    def __init__(self, data_dir: Optional[Path] = None):
        # Default to the project root's metamath2py/classes directory if not specified
        if data_dir is None:
            # Assuming we are in saplings/tools/simple_search_client.py
            # ../../../metamath2py/classes
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.data_dir = base_dir / "metamath2py" / "classes"
        else:
            self.data_dir = Path(data_dir)
            
        self.files: List[Path] = []
        self.label_map: Dict[str, str] = {}
        self._load_label_map()
        self._index_files()

    def _load_label_map(self):
        """Loads the mapping from standard Metamath labels to hashed filenames."""
        map_path = Path(__file__).resolve().parent.parent.parent / "code_builders" / "pythonic_names_map.csv"
        if not map_path.exists():
            LOGGER.warning(f"Label map not found at {map_path}")
            return
            
        try:
            with open(map_path, "r") as f:
                for line in f:
                    if not line.strip(): continue
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        label = parts[0]
                        hash_name = parts[-1] # Usually the last part is the hash
                        self.label_map[label] = hash_name
            LOGGER.info(f"Loaded {len(self.label_map)} labels from map.")
        except Exception as e:
            LOGGER.error(f"Failed to load label map: {e}")

    def _index_files(self):
        if not self.data_dir.exists():
             LOGGER.warning(f"Data directory {self.data_dir} not found.")
             return
        
        self.files = sorted(list(self.data_dir.glob("*.py")))
        LOGGER.info(f"Indexed {len(self.files)} files for simple search in {self.data_dir}.")

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        context_window: int = 40,
        highlight: bool = True,
        phrase_slop: int = 1,
    ) -> List[SearchResult]:
        
        results = []
        query_terms = query.lower().split()
        
        # Check for direct label matches first
        high_priority_files = set()
        
        for term in query_terms:
            # Check if term is a known label
            if term in self.label_map:
                hash_name = self.label_map[term]
                target_file = self.data_dir / f"{hash_name}.py"
                if target_file.exists():
                    high_priority_files.add(target_file)
                    
                    # Add exact match result
                    try:
                        content = target_file.read_text(encoding="utf-8")
                        line_count = content.count("\n") + 1
                        
                        # Enhance snippet with original label info
                        snippet = f"# Original Label: {term} (File: {hash_name}.py)\n" + content[:1000]
                        
                        results.append(SearchResult(
                            path=str(target_file.name), # Use filename as path
                            score=100.0, # High score for exact label match
                            category="exact_match",
                            line_count=line_count,
                            snippet=snippet,
                            start_line=1,
                            end_line=min(line_count, 50)
                        ))
                    except Exception as e:
                        LOGGER.warning(f"Error reading exact match {target_file}: {e}")

        # If we have enough exact matches, return them
        if len(results) >= top_k:
            return results[:top_k]
            
        # Only start content search if we need more results
        if len(results) < top_k:
             import subprocess
             
             # Construct grep regex for OR search: (term1|term2|...)
             # Escape special regex chars in terms just in case
             import re
             safe_terms = [re.escape(t) for t in query_terms if len(t) > 2] # Skip very short terms to avoid noise
             
             if safe_terms:
                 grep_pattern = "|".join(safe_terms)
                 try:
                     # grep -l (filenames only) -r (recursive) -i (case insensitive) -E (extended regex)
                     # We limit to self.data_dir
                     cmd = ["grep", "-l", "-r", "-i", "-E", grep_pattern, str(self.data_dir)]
                     
                     # Check if we have too many matches? grep is fast.
                     # We can pipe to head? No, we need to sort by score.
                     # Let's just run it. grep output on 33k files matching "implies" might be large.
                     # But passing a list of filenames back to Python is faster than reading content.
                     
                     proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10) # 10s timeout
                     
                     if proc.returncode in [0, 1]: # 0=matches, 1=no matches
                         matched_files = proc.stdout.splitlines()
                         
                         LOGGER.info(f"Grep found {len(matched_files)} candidate files.")
                         
                         # Limit processing to max 500 candidates to remain responsive
                         for file_path_str in matched_files[:500]:
                             file_path = Path(file_path_str)
                             if file_path in high_priority_files: continue
                             
                             try:
                                content = file_path.read_text(encoding="utf-8")
                                content_lower = content.lower()
                                
                                score = 0
                                for term in query_terms:
                                    if term in content_lower:
                                        score += 1
                                
                                # Re-verify score > 0 (grep might match substrings or be slightly different)
                                if score > 0:
                                    try:
                                        rel_path = file_path.name
                                    except:
                                        rel_path = str(file_path)
                                        
                                    lines = content.splitlines()
                                    snippet = "\n".join(lines[:20]) 
                                    
                                    results.append(SearchResult(
                                        path=rel_path,
                                        score=float(score),
                                        category="content_match",
                                        line_count=len(lines),
                                        snippet=snippet,
                                        start_line=1,
                                        end_line=20
                                    ))
                             except Exception:
                                 continue
                 except Exception as e:
                     LOGGER.warning(f"Grep search failed: {e}")
                     # Fallback to python loop? No, too slow. Just skip.

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
