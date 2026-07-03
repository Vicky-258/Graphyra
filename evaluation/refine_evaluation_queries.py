import sqlite3
import json
import os


def generate_live_ground_truth():
    db_path = "graphyra.db"
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist yet. Wait for crawl to finish.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Fetch most prominent entities to dynamically map IDs
    cursor.execute("SELECT id, canonical_name, entity_type FROM entities")
    entities = cursor.fetchall()
    ent_map = {name.lower(): id for id, name, _ in entities}
    
    print(f"Loaded {len(entities)} entities from live database.")
    
    def get_chunks_for_entity(entity_name: str, limit: int = 2) -> list:
        ent_id = ent_map.get(entity_name.lower())
        if not ent_id:
            return []
        cursor.execute(
            "SELECT chunk_id FROM entity_mentions WHERE entity_id = ? LIMIT ?",
            (ent_id, limit)
        )
        return [r[0] for r in cursor.fetchall()]

    def get_entity_id(entity_name: str) -> str:
        return ent_map.get(entity_name.lower(), "")

    targets = ["nahida", "ei", "zhongli", "venti", "furina", "traveler", "irminsul", "sumeru", "liyue", "mondstadt", "inazuma", "fontaine"]
    
    active_targets = [t for t in targets if t in ent_map]
    print(f"Active crawl targets found: {active_targets}")
    
    queries = []
    
    # --- Category 1: Direct entity lookup (10 queries) ---
    entity_queries = [
        ("Who is Venti, the Anemo Archon of Mondstadt?", "venti", "Mondstadt", "Easy"),
        ("Who is Ei, the Electro Archon of Inazuma?", "ei", "Inazuma", "Easy"),
        ("Tell me about Zhongli, the consultant of Wangsheng Funeral Parlor.", "zhongli", "Liyue", "Easy"),
        ("Who is Nahida, the Lesser Lord Kusanali of Sumeru?", "nahida", "Sumeru", "Easy"),
        ("Who is Furina, the former hydro archon of Fontaine?", "furina", "Fontaine", "Easy"),
        ("Who is the Traveler searching for their lost sibling?", "traveler", "Traveler", "Easy"),
        ("Explain what the Akasha System is in Sumeru.", "nahida", "Sumeru", "Medium"),
        ("What is the nation of Liyue known for?", "liyue", "Liyue", "Easy"),
        ("What is the city of Mondstadt known for?", "mondstadt", "Mondstadt", "Easy"),
        ("What is the nation of Inazuma known for?", "inazuma", "Inazuma", "Easy"),
    ]
    
    for q_text, primary, secondary, diff in entity_queries:
        prim_id = get_entity_id(primary)
        sec_id = get_entity_id(secondary)
        if prim_id:
            chunks = get_chunks_for_entity(primary, 2)
            if chunks:
                queries.append({
                    "query": q_text,
                    "expected_entities": [prim_id] + ([sec_id] if sec_id else []),
                    "expected_chunks": chunks,
                    "category": "Direct entity lookup",
                    "difficulty": diff
                })

    # --- Category 2: Alias resolution (10 queries) ---
    alias_queries = [
        ("Who is Beelzebul, the twin sister of Baal?", "ei", "Easy"),
        ("Who is Morax, the God of Contracts?", "zhongli", "Easy"),
        ("Who is Barbatos, the God of Freedom?", "venti", "Easy"),
        ("Who is Lesser Lord Kusanali?", "nahida", "Easy"),
        ("Who is Rex Lapis of Liyue Harbor?", "zhongli", "Easy"),
        ("Who is the Deity of Eternity in Inazuma?", "ei", "Easy"),
        ("Who is the God of Wisdom in Sumeru?", "nahida", "Easy"),
        ("Who is Focalors, the Hydro Archon of Fontaine?", "furina", "Medium"),
        ("Who is the Lesser Lord of Sumeru?", "nahida", "Easy"),
        ("Who is the Geo Archon of Liyue?", "zhongli", "Easy"),
    ]
    for q_text, target, diff in alias_queries:
        t_id = get_entity_id(target)
        if t_id:
            chunks = get_chunks_for_entity(target, 2)
            if chunks:
                queries.append({
                    "query": q_text,
                    "expected_entities": [t_id],
                    "expected_chunks": chunks,
                    "category": "Alias resolution",
                    "difficulty": diff
                })

    # --- Category 3: Relationship queries (10 queries) ---
    # Map artifact relationships back to entity connections
    cursor.execute("SELECT source_id, target_id, relation_type FROM relations LIMIT 2000")
    db_relations = cursor.fetchall()
    
    relations_found = []
    for src_id, tgt_id, rel_type in db_relations:
        src_name = src_id.replace("genshin_fandom:main:", "").replace("_", " ")
        tgt_name = tgt_id.replace("genshin_fandom:main:", "").replace("_", " ")
        
        src_ent_id = get_entity_id(src_name)
        tgt_ent_id = get_entity_id(tgt_name)
        
        if src_ent_id and tgt_ent_id and src_ent_id != tgt_ent_id:
            relations_found.append((src_name, tgt_name, src_ent_id, tgt_ent_id))
            
    print(f"Mapped {len(relations_found)} entity relationships from document links.")
    
    added_rels = set()
    for src_name, tgt_name, src_id, tgt_id in relations_found:
        pair_key = tuple(sorted([src_id, tgt_id]))
        if pair_key in added_rels:
            continue
        added_rels.add(pair_key)
        chunks = list(set(get_chunks_for_entity(src_name, 1) + get_chunks_for_entity(tgt_name, 1)))
        if chunks:
            queries.append({
                "query": f"Explain the relationship between {src_name} and {tgt_name} in the story.",
                "expected_entities": [src_id, tgt_id],
                "expected_chunks": chunks,
                "category": "Relationship queries",
                "difficulty": "Medium"
            })
            if len(added_rels) >= 10:
                break

    # --- Category 4: Multi-hop reasoning (10 queries) ---
    multihop_scenarios = [
        ("Who is the successor of Greater Lord Rukkhadevata in Sumeru?", "nahida", "irminsul", "Hard"),
        ("How are Ley Lines connected to the Irminsul world tree?", "irminsul", "sumeru", "Medium"),
        ("Who did Barbatos meet in Liyue after the Archon War?", "venti", "zhongli", "Hard"),
        ("What is the relationship between the Raiden Shogun puppet and Ei?", "ei", "inazuma", "Medium"),
        ("Who is the successorship lineage of Sumeru's world tree protector?", "nahida", "irminsul", "Hard"),
        ("Who ruled Sumeru before Lesser Lord Kusanali?", "nahida", "sumeru", "Hard"),
        ("Find Ley Line links associated with Irminsul branches.", "irminsul", "sumeru", "Hard"),
        ("Explain Venti's past links to Zhongli in Liyue Harbor.", "venti", "zhongli", "Hard"),
        ("How is the Akasha terminal linked to Lesser Lord Kusanali?", "nahida", "sumeru", "Medium"),
        ("Who is Rukkhadevata in relation to Lesser Lord Kusanali?", "nahida", "irminsul", "Hard"),
    ]
    for q_text, ent1, ent2, diff in multihop_scenarios:
        id1 = get_entity_id(ent1)
        id2 = get_entity_id(ent2)
        chunks = list(set(get_chunks_for_entity(ent1, 1) + get_chunks_for_entity(ent2, 1)))
        if id1 and id2 and chunks:
            queries.append({
                "query": q_text,
                "expected_entities": [id1, id2],
                "expected_chunks": chunks,
                "category": "Multi-hop reasoning",
                "difficulty": diff
            })

    # --- Category 5: Conceptual questions (10 queries) ---
    conceptual_scenarios = [
        ("What is the silver-white tree Irminsul that grows in Teyvat?", "irminsul", "Medium"),
        ("How does information and memory get added to the repository of Teyvat?", "irminsul", "Hard"),
        ("What happens when an entire being is removed from Irminsul?", "irminsul", "Hard"),
        ("What is the concept of eternity in the nation of Inazuma?", "ei", "Medium"),
        ("What is the Geo Archon's philosophy of contracts in Liyue?", "zhongli", "Medium"),
        ("Describe the concept of wind-guided freedom in Mondstadt.", "venti", "Medium"),
        ("What is the history of the Fontaine nation?", "fontaine", "Medium"),
        ("Explain the Ley Lines concept in Teyvat's world layout.", "irminsul", "Hard"),
        ("How does Lesser Lord Kusanali use Akasha terminals?", "nahida", "Medium"),
        ("What is the role of an Archon in Teyvat?", "traveler", "Hard"),
    ]
    for q_text, ent, diff in conceptual_scenarios:
        e_id = get_entity_id(ent)
        chunks = get_chunks_for_entity(ent, 2)
        if e_id and chunks:
            queries.append({
                "query": q_text,
                "expected_entities": [e_id],
                "expected_chunks": chunks,
                "category": "Conceptual questions",
                "difficulty": diff
            })

    # --- Category 6: Hidden entity questions (10 queries) ---
    hidden_scenarios = [
        ("What point of interest is located on the eastern side of Dragonspine?", "irminsul", "Hard"),
        ("What tree was once revered by the ancient city of Sal Vindagnyr?", "irminsul", "Hard"),
        ("Where does Albedo conduct his research on Dragonspine?", "mondstadt", "Hard"),
        ("Find details about the Frostbearing Tree tree node.", "irminsul", "Hard"),
        ("Where is the research laboratory of Albedo on the snow mountain?", "mondstadt", "Hard"),
        ("Tell me about the twin sister of Baal that died in the cataclysm.", "ei", "Hard"),
        ("What was Liyue Harbor called before the Archon War?", "liyue", "Hard"),
        ("Who is the twin sister of Beelzebul that died in Khaenri'ah?", "ei", "Hard"),
        ("What was the assembly in Liyue before Liyue Harbor was founded?", "liyue", "Hard"),
        ("Who is the Yaksha whose true name is unknown, born 4000 years ago?", "zhongli", "Hard"),
    ]
    for q_text, ent, diff in hidden_scenarios:
        e_id = get_entity_id(ent)
        chunks = get_chunks_for_entity(ent, 1)
        if e_id and chunks:
            queries.append({
                "query": q_text,
                "expected_entities": [e_id],
                "expected_chunks": chunks,
                "category": "Hidden entity questions",
                "difficulty": diff
            })

    # --- Category 7: Comparative questions (10 queries) ---
    comparative_scenarios = [
        ("Compare Venti and Zhongli as archons of Mondstadt and Liyue.", "venti", "zhongli", "Medium"),
        ("Compare the eternity of Inazuma with the contracts of Liyue.", "ei", "zhongli", "Hard"),
        ("Compare Lesser Lord Kusanali and Greater Lord Rukkhadevata's rule.", "nahida", "irminsul", "Medium"),
        ("Compare Mondstadt's freedom and Inazuma's eternity concept.", "venti", "ei", "Hard"),
        ("Compare the Frostbearing Tree and Irminsul world tree functions.", "irminsul", "irminsul", "Medium"),
        ("Compare Furina of Fontaine with Venti of Mondstadt.", "furina", "venti", "Medium"),
        ("Compare Liyue's Archon War and Inazuma's Archon War outcomes.", "liyue", "inazuma", "Hard"),
        ("Compare Lesser Lord Kusanali's Akademia isolation and Zhongli's retired life.", "nahida", "zhongli", "Hard"),
        ("Compare Mondstadt and Fontaine's governance structures.", "venti", "furina", "Hard"),
        ("Compare Raiden Ei's Plane of Euthymia with Nahida's dream traversal.", "ei", "nahida", "Hard"),
    ]
    for q_text, ent1, ent2, diff in comparative_scenarios:
        id1 = get_entity_id(ent1)
        id2 = get_entity_id(ent2)
        chunks = list(set(get_chunks_for_entity(ent1, 1) + get_chunks_for_entity(ent2, 1)))
        if id1 and id2 and chunks:
            queries.append({
                "query": q_text,
                "expected_entities": [id1, id2],
                "expected_chunks": chunks,
                "category": "Comparative questions",
                "difficulty": diff
            })

    # --- Category 8: Attribute questions (10 queries) ---
    attribute_scenarios = [
        ("What is the entity type of Irminsul in the knowledge base?", "irminsul", "Easy"),
        ("What is the entity type of Zhongli in Liyue?", "zhongli", "Easy"),
        ("What is the canonical name of Lesser Lord Kusanali?", "nahida", "Easy"),
        ("What is the entity type of Venti in Mondstadt?", "venti", "Easy"),
        ("What is the entity type of Furina in Fontaine?", "furina", "Easy"),
        ("What is the entity type of Ei in Inazuma?", "ei", "Easy"),
        ("What is the entity type of Traveler?", "traveler", "Easy"),
        ("What is the entity type of Sumeru nation?", "sumeru", "Easy"),
        ("What is the entity type of Liyue nation?", "liyue", "Easy"),
        ("What is the entity type of Fontaine nation?", "fontaine", "Easy"),
    ]
    for q_text, ent, diff in attribute_scenarios:
        e_id = get_entity_id(ent)
        chunks = get_chunks_for_entity(ent, 1)
        if e_id and chunks:
            queries.append({
                "query": q_text,
                "expected_entities": [e_id],
                "expected_chunks": chunks,
                "category": "Attribute questions",
                "difficulty": diff
            })

    conn.close()
    
    # Save the live, validated ground truth file
    os.makedirs("evaluation/retrieval", exist_ok=True)
    with open("evaluation/retrieval/ground_truth_large.json", "w") as f:
        json.dump(queries, f, indent=2)
        
    print(f"Successfully generated {len(queries)} validated queries based on live crawled database.")


if __name__ == "__main__":
    generate_live_ground_truth()
