import json
import os


def build_gold_standard():
    # Correct entity IDs:
    # ENT_001 -> Ei
    # ENT_002 -> Nahida
    # ENT_003 -> Mondstadt
    # ENT_004 -> Traveler
    # ENT_005 -> Venti
    # ENT_006 -> Irminsul
    # ENT_007 -> Furina
    # ENT_008 -> Zhongli
    # ENT_009 -> Fontaine
    # ENT_010 -> Inazuma
    # ENT_011 -> Liyue
    # ENT_012 -> Sumeru

    gold_truth = [
        # --- 1. Direct entity lookup (13 queries) ---
        {
            "query": "Who is Venti, the Anemo Archon of Mondstadt?",
            "expected_entities": ["ENT_005", "ENT_003"],
            "expected_chunks": ["CHK_222", "CHK_240"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Ei, the Electro Archon of Inazuma?",
            "expected_entities": ["ENT_001", "ENT_010"],
            "expected_chunks": ["CHK_002", "CHK_003"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Zhongli, the consultant of Wangsheng Funeral Parlor?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291", "CHK_303"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Nahida, the Lesser Lord Kusanali of Sumeru?",
            "expected_entities": ["ENT_002", "ENT_012"],
            "expected_chunks": ["CHK_037", "CHK_458"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Furina, the former hydro archon of Fontaine?",
            "expected_entities": ["ENT_007", "ENT_009"],
            "expected_chunks": ["CHK_263", "CHK_264"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "Tell me about the Traveler searching for their sibling.",
            "expected_entities": ["ENT_004"],
            "expected_chunks": ["CHK_020", "CHK_069"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is Mondstadt?",
            "expected_entities": ["ENT_003"],
            "expected_chunks": ["CHK_069"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is Liyue?",
            "expected_entities": ["ENT_011"],
            "expected_chunks": ["CHK_409"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is Inazuma?",
            "expected_entities": ["ENT_010"],
            "expected_chunks": ["CHK_372"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is Sumeru?",
            "expected_entities": ["ENT_012"],
            "expected_chunks": ["CHK_458"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is Fontaine?",
            "expected_entities": ["ENT_009"],
            "expected_chunks": ["CHK_319"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is Irminsul?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_002", "CHK_005"],
            "category": "Direct entity lookup",
            "difficulty": "Easy"
        },
        {
            "query": "What is the Akasha System?",
            "expected_entities": ["ENT_002", "ENT_012"],
            "expected_chunks": ["CHK_003", "CHK_004"],
            "category": "Direct entity lookup",
            "difficulty": "Medium"
        },

        # --- 2. Alias resolution (13 queries) ---
        {
            "query": "Who is Beelzebul?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_027"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Morax?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291", "CHK_009"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Barbatos?",
            "expected_entities": ["ENT_005"],
            "expected_chunks": ["CHK_222", "CHK_009"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Lesser Lord Kusanali?",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_037", "CHK_458"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Rex Lapis?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291", "CHK_009"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is the God of Contracts?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291", "CHK_409"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is the God of Freedom?",
            "expected_entities": ["ENT_005"],
            "expected_chunks": ["CHK_222", "CHK_069"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is the God of Eternity?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_372"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is the God of Wisdom?",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_037", "CHK_458"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Focalors?",
            "expected_entities": ["ENT_007"],
            "expected_chunks": ["CHK_263", "CHK_319"],
            "category": "Alias resolution",
            "difficulty": "Medium"
        },
        {
            "query": "Who is Baal?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is the Shadow Shogun?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Alias resolution",
            "difficulty": "Easy"
        },
        {
            "query": "Who is Lesser Lord Kusanali's predecessor?",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_003", "CHK_004"],
            "category": "Alias resolution",
            "difficulty": "Medium"
        },

        # --- 3. Relationship queries (13 queries) ---
        {
            "query": "What is the relationship between Ei and Makoto?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Relationship queries",
            "difficulty": "Medium"
        },
        {
            "query": "How are Yae Miko and Ei connected?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_003", "CHK_010"],
            "category": "Relationship queries",
            "difficulty": "Easy"
        },
        {
            "query": "What is the connection between Zhongli and the Wangsheng Funeral Parlor?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291", "CHK_365"],
            "category": "Relationship queries",
            "difficulty": "Medium"
        },
        {
            "query": "How are Venti and Dvalin related?",
            "expected_entities": ["ENT_005"],
            "expected_chunks": ["CHK_222", "CHK_240"],
            "category": "Relationship queries",
            "difficulty": "Medium"
        },
        {
            "query": "How are Nahida and Rukkhadevata related?",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_003", "CHK_004"],
            "category": "Relationship queries",
            "difficulty": "Hard"
        },
        {
            "query": "What is the link between Raiden Ei and Kunikuzushi?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009", "CHK_022"],
            "category": "Relationship queries",
            "difficulty": "Hard"
        },
        {
            "query": "How did Ei meet Morax and Barbatos?",
            "expected_entities": ["ENT_001", "ENT_008", "ENT_005"],
            "expected_chunks": ["CHK_009"],
            "category": "Relationship queries",
            "difficulty": "Hard"
        },
        {
            "query": "What is the relationship between Kujou Sara and the Raiden Shogun?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_016"],
            "category": "Relationship queries",
            "difficulty": "Easy"
        },
        {
            "query": "What is the relationship between Sangonomiya Kokomi and the Raiden Shogun?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_018"],
            "category": "Relationship queries",
            "difficulty": "Medium"
        },
        {
            "query": "How are Albedo and the Traveler related?",
            "expected_entities": ["ENT_004"],
            "expected_chunks": ["CHK_1875"],
            "category": "Relationship queries",
            "difficulty": "Medium"
        },
        {
            "query": "What is the link between Zhongli and Guizhong?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_2292"],
            "category": "Relationship queries",
            "difficulty": "Hard"
        },
        {
            "query": "What is the connection between Ei and Mikoshi Chiyo?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009"],
            "category": "Relationship queries",
            "difficulty": "Hard"
        },
        {
            "query": "What is the connection between Ei and Kitsune Saiguu?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009"],
            "category": "Relationship queries",
            "difficulty": "Hard"
        },

        # --- 4. Multi-hop reasoning (13 queries) ---
        {
            "query": "Who is the successor of Greater Lord Rukkhadevata in Sumeru?",
            "expected_entities": ["ENT_002", "ENT_006"],
            "expected_chunks": ["CHK_037", "CHK_458"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "How are Ley Lines connected to the Irminsul world tree?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_002", "CHK_005"],
            "category": "Multi-hop reasoning",
            "difficulty": "Medium"
        },
        {
            "query": "What bow is forged using Irminsul branches?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_010", "CHK_002"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Why did Ei entrust her Electro Gnosis to Yae Miko?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_003", "CHK_010"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Who did the Traveler defeat in the Plane of Euthymia?",
            "expected_entities": ["ENT_004", "ENT_001"],
            "expected_chunks": ["CHK_011"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Why did Orobashi attack Yashiori Island?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_008"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Who is the current Electro Archon ruled Inazuma under the name Baal?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_003"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Who created the Scaramouche puppet and why was he sealed?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009", "CHK_022"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Who was the Shadow warrior shadow shogun of Baal?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "How did Ei fight Mikoshi Chiyo after the cataclysm?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Who faked his death during Liyue's Rite of Descension?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_011", "CHK_024"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Who helped the Traveler defeat Raiden Ei inside the Plane of Euthymia?",
            "expected_entities": ["ENT_001", "ENT_004"],
            "expected_chunks": ["CHK_011"],
            "category": "Multi-hop reasoning",
            "difficulty": "Hard"
        },
        {
            "query": "Why was the Sakoku Decree abolished in Inazuma?",
            "expected_entities": ["ENT_001", "ENT_010"],
            "expected_chunks": ["CHK_012"],
            "category": "Multi-hop reasoning",
            "difficulty": "Medium"
        },

        # --- 5. Conceptual questions (12 queries) ---
        {
            "query": "What is the concept of eternity in Inazuma?",
            "expected_entities": ["ENT_001", "ENT_010"],
            "expected_chunks": ["CHK_002", "CHK_016"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "What is the Geo Archon's philosophy of contracts?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291", "CHK_303"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "Describe the concept of wind-guided freedom in Mondstadt.",
            "expected_entities": ["ENT_005", "ENT_003"],
            "expected_chunks": ["CHK_222", "CHK_019"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "What happens when someone is removed from Irminsul?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_005", "CHK_006"],
            "category": "Conceptual questions",
            "difficulty": "Hard"
        },
        {
            "query": "How does the Akasha System collect knowledge?",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_003", "CHK_004"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "Explain the erosion that affects ancient beings in Teyvat.",
            "expected_entities": ["ENT_008", "ENT_001"],
            "expected_chunks": ["CHK_009", "CHK_018"],
            "category": "Conceptual questions",
            "difficulty": "Hard"
        },
        {
            "query": "What is the role of an Archon according to Celestia?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_003", "CHK_008"],
            "category": "Conceptual questions",
            "difficulty": "Hard"
        },
        {
            "query": "What is the Sakoku Decree and its purpose?",
            "expected_entities": ["ENT_010"],
            "expected_chunks": ["CHK_010", "CHK_012"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "What is the Vision Hunt Decree and its purpose?",
            "expected_entities": ["ENT_010"],
            "expected_chunks": ["CHK_010", "CHK_011"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "What are the Ley Lines of Teyvat?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_002", "CHK_005"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },
        {
            "query": "What is the Musou no Hitotachi sword technique?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_026"],
            "category": "Conceptual questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the Plane of Euthymia?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_003"],
            "category": "Conceptual questions",
            "difficulty": "Medium"
        },

        # --- 6. Hidden entity questions (12 queries) ---
        {
            "query": "What tree grows on the eastern side of Dragonspine?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_009", "CHK_2162"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Which tree was worshipped by the ancient city of Sal Vindagnyr?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_009", "CHK_2163"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Where is Albedo's camp on the snow mountain?",
            "expected_entities": ["ENT_003"],
            "expected_chunks": ["CHK_1875"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Who was the twin sister of Baal that died in Khaenri'ah?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Who is the Conqueror of Demons born 4000 years ago?",
            "expected_entities": ["ENT_011", "ENT_008"],
            "expected_chunks": ["CHK_4493"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "What was Liyue Harbor called before Liyue was unified?",
            "expected_entities": ["ENT_011", "ENT_008"],
            "expected_chunks": ["CHK_2292"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "What was the assembly founded by Guizhong and Morax?",
            "expected_entities": ["ENT_011", "ENT_008"],
            "expected_chunks": ["CHK_2292"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Which youkai friend of Ei died defending Inazuma from the Abyss?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Which swordsmithing schools are collectively known as the Raiden Gokaden?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_015"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "Who is the Tengu general of the Tenryou Commission?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_016"],
            "category": "Hidden entity questions",
            "difficulty": "Easy"
        },
        {
            "query": "Which bow uses the wood of the world tree for its body?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_010", "CHK_002"],
            "category": "Hidden entity questions",
            "difficulty": "Hard"
        },
        {
            "query": "What is the divine name of the twin god Makoto?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Hidden entity questions",
            "difficulty": "Medium"
        },

        # --- 7. Comparative questions (12 queries) ---
        {
            "query": "Compare Venti and Zhongli as archons of Mondstadt and Liyue.",
            "expected_entities": ["ENT_005", "ENT_008"],
            "expected_chunks": ["CHK_009", "CHK_022"],
            "category": "Comparative questions",
            "difficulty": "Medium"
        },
        {
            "query": "Compare the eternity of Inazuma with the contracts of Liyue.",
            "expected_entities": ["ENT_001", "ENT_008"],
            "expected_chunks": ["CHK_014", "CHK_024"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare Lesser Lord Kusanali and Greater Lord Rukkhadevata.",
            "expected_entities": ["ENT_002", "ENT_006"],
            "expected_chunks": ["CHK_003", "CHK_004"],
            "category": "Comparative questions",
            "difficulty": "Medium"
        },
        {
            "query": "Compare the Frostbearing Tree and Irminsul world tree functions.",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_002", "CHK_2163"],
            "category": "Comparative questions",
            "difficulty": "Medium"
        },
        {
            "query": "Compare Furina of Fontaine with Venti of Mondstadt.",
            "expected_entities": ["ENT_007", "ENT_005"],
            "expected_chunks": ["CHK_050", "CHK_145"],
            "category": "Comparative questions",
            "difficulty": "Medium"
        },
        {
            "query": "Compare Liyue's Archon War and Inazuma's Archon War outcomes.",
            "expected_entities": ["ENT_011", "ENT_010"],
            "expected_chunks": ["CHK_008", "CHK_022"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare Raiden Ei's Plane of Euthymia with Nahida's dream traversal.",
            "expected_entities": ["ENT_001", "ENT_002"],
            "expected_chunks": ["CHK_003", "CHK_004"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare Mondstadt's freedom and Inazuma's eternity concept.",
            "expected_entities": ["ENT_003", "ENT_010"],
            "expected_chunks": ["CHK_014", "CHK_019"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare Kujou Sara and Gorou as loyal generals.",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_016"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare the Akasha terminal system with the Ley Line system.",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_003", "CHK_005"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare the Sacred Sakura tree and the Frostbearing Tree.",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_009", "CHK_2162"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },
        {
            "query": "Compare Baal and Beelzebul's approach to ruling Inazuma.",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_002", "CHK_008"],
            "category": "Comparative questions",
            "difficulty": "Hard"
        },

        # --- 8. Attribute questions (12 queries) ---
        {
            "query": "What is the entity type of Irminsul?",
            "expected_entities": ["ENT_006"],
            "expected_chunks": ["CHK_002"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Zhongli?",
            "expected_entities": ["ENT_008"],
            "expected_chunks": ["CHK_291"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the canonical name of Lesser Lord Kusanali?",
            "expected_entities": ["ENT_002"],
            "expected_chunks": ["CHK_002"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Venti?",
            "expected_entities": ["ENT_005"],
            "expected_chunks": ["CHK_222"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Furina?",
            "expected_entities": ["ENT_007"],
            "expected_chunks": ["CHK_050"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Ei?",
            "expected_entities": ["ENT_001"],
            "expected_chunks": ["CHK_001"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Traveler?",
            "expected_entities": ["ENT_004"],
            "expected_chunks": ["CHK_024"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Sumeru?",
            "expected_entities": ["ENT_012"],
            "expected_chunks": ["CHK_003"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Liyue?",
            "expected_entities": ["ENT_011"],
            "expected_chunks": ["CHK_145"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Fontaine?",
            "expected_entities": ["ENT_009"],
            "expected_chunks": ["CHK_050"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Mondstadt?",
            "expected_entities": ["ENT_003"],
            "expected_chunks": ["CHK_050"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        },
        {
            "query": "What is the entity type of Inazuma?",
            "expected_entities": ["ENT_010"],
            "expected_chunks": ["CHK_014"],
            "category": "Attribute questions",
            "difficulty": "Easy"
        }
    ]
    
    os.makedirs("evaluation/retrieval", exist_ok=True)
    with open("evaluation/retrieval/ground_truth_large.json", "w") as f:
        json.dump(gold_truth, f, indent=2)
        
    print(f"Successfully compiled exactly {len(gold_truth)} gold-standard queries to evaluation/retrieval/ground_truth_large.json")


if __name__ == "__main__":
    build_gold_standard()
