import re
import datetime
from typing import Optional, Set
from graphyra.models.entity import Entity
from graphyra.utils.entity_type import EntityType
from graphyra.config.ingestion import DEFAULT_INGESTION_ENTITY_TYPE
from graphyra.storage.entity_repository import EntityRepository
from graphyra.storage.alias_manager import AliasManager
from graphyra.storage.mention_repository import MentionRepository
from graphyra.storage.relation_repository import RelationRepository
from graphyra.storage.chunk_repository import ChunkRepository
from graphyra.storage.evidence_repository import EvidenceRepository


class AnchorResolver:

    def __init__(self, storage):
        self.storage = storage
        self.entity_repo = EntityRepository(storage)
        self.alias_manager = AliasManager(storage)
        self.mention_repo = MentionRepository(storage)
        self.relation_repo = RelationRepository(storage)
        self.chunk_repo = ChunkRepository(storage)
        self.evidence_repo = EvidenceRepository(storage)

    def resolve(
        self,
        name: str,
        create_if_missing: bool = False,
        default_type: EntityType = None
    ) -> Optional[Entity]:
        """
        Resolves a name reference to an existing retrieval anchor (Entity).
        Order of resolution:
        1. Clean and normalize name.
        2. Exact name match.
        3. Alias match.
        4. Case-insensitive lookup.
        5. If not found and create_if_missing is True, create a new anchor.
        """
        if default_type is None:
            default_type = DEFAULT_INGESTION_ENTITY_TYPE

        cleaned_name = " ".join(name.strip().split())
        if not cleaned_name:
            return None

        # 1. Exact match
        entity = self.entity_repo.find_by_name(cleaned_name)
        if entity:
            return entity

        # 2. Alias match
        matching_ids = self.alias_manager.find_by_alias(cleaned_name)
        if matching_ids:
            ent = self.entity_repo.get(matching_ids[0])
            if ent:
                return ent

        # 3. Case-insensitive lookup (handled by step 1 find_by_name)
        pass

        # 4. Create new if requested
        if create_if_missing:
            new_entity = self.entity_repo.create(
                canonical_name=cleaned_name,
                entity_type=default_type,
                metadata={"auto_created": True, "created_at": datetime.datetime.now().isoformat()}
            )
            self.alias_manager.add_alias(new_entity.id, cleaned_name)
            return new_entity

        return None

    def score_similarity(self, anchor_id_1: str, anchor_id_2: str) -> float:
        """
        Calculates similarity score [0.0, 1.0] between two retrieval anchors.
        Uses name overlap, alias overlap, context (chunk content) similarity, and relation neighborhood similarity.
        """
        if anchor_id_1 == anchor_id_2:
            return 1.0

        ent1 = self.entity_repo.get(anchor_id_1)
        ent2 = self.entity_repo.get(anchor_id_2)
        if not ent1 or not ent2:
            return 0.0

        scores = []
        weights = []

        # --- 1. Name & Alias similarity ---
        names1 = {ent1.canonical_name.lower()} | {a.lower() for a in self.alias_manager.get_aliases(anchor_id_1)}
        names2 = {ent2.canonical_name.lower()} | {a.lower() for a in self.alias_manager.get_aliases(anchor_id_2)}
        
        name_intersection = names1 & names2
        name_union = names1 | names2
        name_score = len(name_intersection) / len(name_union) if name_union else 0.0
        scores.append(name_score)
        weights.append(0.4)

        # --- 2. Context overlap similarity (Jaccard similarity of tokenized chunks) ---
        chunks1 = self.mention_repo.get_chunks_for_entity(anchor_id_1)
        chunks2 = self.mention_repo.get_chunks_for_entity(anchor_id_2)

        def get_chunk_tokens(chunk_ids) -> Set[str]:
            tokens = set()
            for cid in chunk_ids:
                c = self.chunk_repo.get(cid)
                if c and c.content:
                    words = re.findall(r"\w+", c.content.lower())
                    tokens.update(words)
            return tokens

        tokens1 = get_chunk_tokens(chunks1)
        tokens2 = get_chunk_tokens(chunks2)
        
        if tokens1 or tokens2:
            context_intersection = tokens1 & tokens2
            context_union = tokens1 | tokens2
            context_score = len(context_intersection) / len(context_union) if context_union else 0.0
            scores.append(context_score)
            weights.append(0.3)

        # --- 3. Relation Neighborhood similarity ---
        def get_neighbors(entity_id) -> Set[str]:
            return set(self.relation_repo.get_connected_nodes(entity_id))

        neighbors1 = get_neighbors(anchor_id_1)
        neighbors2 = get_neighbors(anchor_id_2)

        if neighbors1 or neighbors2:
            neighbor_intersection = neighbors1 & neighbors2
            neighbor_union = neighbors1 | neighbors2
            neighbor_score = len(neighbor_intersection) / len(neighbor_union) if neighbor_union else 0.0
            scores.append(neighbor_score)
            weights.append(0.3)

        if not scores:
            return 0.0
        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def merge(self, source_anchor_id: str, target_anchor_id: str):
        """
        Merges the source anchor into the target anchor.
        Updates mentions, aliases, relations, and evidence references.
        Deletes the source anchor.
        """
        if source_anchor_id == target_anchor_id:
            return

        source_ent = self.entity_repo.get(source_anchor_id)
        target_ent = self.entity_repo.get(target_anchor_id)
        if not source_ent or not target_ent:
            return

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Transfer Aliases
            self.alias_manager.add_alias(target_anchor_id, source_ent.canonical_name)
            source_aliases = self.alias_manager.get_aliases(source_anchor_id)
            for a in source_aliases:
                self.alias_manager.add_alias(target_anchor_id, a)

            # 2. Transfer mentions
            target_chunks = set(self.mention_repo.get_chunks_for_entity(target_anchor_id))
            source_chunks = self.mention_repo.get_chunks_for_entity(source_anchor_id)
            
            for chunk_id in source_chunks:
                if chunk_id in target_chunks:
                    cursor.execute(
                        "DELETE FROM entity_mentions WHERE entity_id = ? AND chunk_id = ?",
                        (source_anchor_id, chunk_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ? AND chunk_id = ?",
                        (target_anchor_id, source_anchor_id, chunk_id)
                    )

            # 3. Transfer relations
            cursor.execute(
                "SELECT id, source_id, target_id, relation_type, metadata FROM relations WHERE source_id = ? OR target_id = ?",
                (source_anchor_id, source_anchor_id)
            )
            relations_to_update = cursor.fetchall()
            
            for rel_id, s_id, t_id, rel_type, meta in relations_to_update:
                new_s_id = target_anchor_id if s_id == source_anchor_id else s_id
                new_t_id = target_anchor_id if t_id == source_anchor_id else t_id

                if new_s_id == new_t_id:
                    cursor.execute("DELETE FROM relations WHERE id = ?", (rel_id,))
                    continue

                cursor.execute(
                    "SELECT id FROM relations WHERE source_id = ? AND target_id = ? AND relation_type = ?",
                    (new_s_id, new_t_id, rel_type)
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        "UPDATE evidence_references SET relation_id = ? WHERE relation_id = ?",
                        (existing[0], rel_id)
                    )
                    cursor.execute("DELETE FROM relations WHERE id = ?", (rel_id,))
                else:
                    cursor.execute(
                        "UPDATE relations SET source_id = ?, target_id = ? WHERE id = ?",
                        (new_s_id, new_t_id, rel_id)
                    )

            # 4. Transfer Evidence References
            cursor.execute(
                "UPDATE evidence_references SET entity_id = ? WHERE entity_id = ?",
                (target_anchor_id, source_anchor_id)
            )

            # 5. Delete source entity record
            cursor.execute("DELETE FROM entities WHERE id = ?", (source_anchor_id,))
            conn.commit()

    def generate_and_register_simplified_aliases(self, entity: Entity):
        """
        Generates and registers simplified aliases for an entity name containing
        parentheses, slashes, or quotes.
        """
        name = entity.canonical_name
        aliases = []
        
        # 1. Handle parentheses: Kitsune (Species) -> Kitsune (excluding disambiguation pages)
        if "(" in name and ")" in name:
            if "disambiguation" not in name.lower():
                simplified = re.sub(r'\(.*?\)', '', name).strip()
                if simplified and simplified != name:
                    aliases.append(simplified)
                
        # 2. Handle double quotes: "Boatman" -> Boatman
        if '"' in name:
            simplified = name.replace('"', '').strip()
            if simplified and simplified != name:
                aliases.append(simplified)
                
        for alias_val in set(aliases):
            if alias_val.lower() == name.lower():
                continue
            
            # Avoid duplicate alias checks
            existing = {a.lower() for a in self.alias_manager.get_aliases(entity.id)}
            if alias_val.lower() in existing:
                continue
                
            # Check if this alias matches any existing entity canonical name to prevent conflicts
            colliding = self.entity_repo.find_by_name(alias_val)
            if colliding:
                continue
                
            self.alias_manager.add_alias(entity.id, alias_val)

    def register_redirect(self, source_title: str, target_title: str):
        """
        Registers a redirect alias from source_title to target_title.
        Resolves or creates the target anchor and maps source_title as an alias to it.
        """
        target_anchor = self.resolve(target_title, create_if_missing=True)
        
        cleaned_source = " ".join(source_title.strip().split())
        if not cleaned_source:
            return
            
        # Register source_title as alias of target_anchor if not already registered
        existing = {a.lower() for a in self.alias_manager.get_aliases(target_anchor.id)}
        if cleaned_source.lower() not in existing:
            self.alias_manager.add_alias(target_anchor.id, cleaned_source)

