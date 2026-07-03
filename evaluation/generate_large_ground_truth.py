import json
import os

ground_truth_data = [
    # 1. Entity (10 queries)
    {
        "query": "Who is Venti, the Anemo Archon of Mondstadt?",
        "expected_entities": ["ENT_004", "ENT_003"],
        "expected_chunks": ["CHK_049", "CHK_050"],
        "category": "Entity"
    },
    {
        "query": "Who is Ei, the Electro Archon of Inazuma?",
        "expected_entities": ["ENT_002", "ENT_008"],
        "expected_chunks": ["CHK_014", "CHK_015"],
        "category": "Entity"
    },
    {
        "query": "Tell me about Zhongli, the consultant of Wangsheng Funeral Parlor.",
        "expected_entities": ["ENT_009"],
        "expected_chunks": ["CHK_022", "CHK_024"],
        "category": "Entity"
    },
    {
        "query": "Who is Nahida, the Lesser Lord Kusanali of Sumeru?",
        "expected_entities": ["ENT_010"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Entity"
    },
    {
        "query": "Who is Furina, the former hydro archon of Fontaine?",
        "expected_entities": ["ENT_005", "ENT_011"],
        "expected_chunks": ["CHK_050", "CHK_145"],
        "category": "Entity"
    },
    {
        "query": "Who is the Traveler searching for their lost sibling?",
        "expected_entities": ["ENT_007"],
        "expected_chunks": ["CHK_024", "CHK_049"],
        "category": "Entity"
    },
    {
        "query": "Explain what the Akasha System is in Sumeru.",
        "expected_entities": ["ENT_010"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Entity"
    },
    {
        "query": "What is the nation of Liyue known for?",
        "expected_entities": ["ENT_006"],
        "expected_chunks": ["CHK_145", "CHK_146"],
        "category": "Entity"
    },
    {
        "query": "What is the city of Mondstadt known for?",
        "expected_entities": ["ENT_003"],
        "expected_chunks": ["CHK_050", "CHK_051"],
        "category": "Entity"
    },
    {
        "query": "What is the nation of Inazuma known for?",
        "expected_entities": ["ENT_008"],
        "expected_chunks": ["CHK_014", "CHK_016"],
        "category": "Entity"
    },

    # 2. Alias (7 queries)
    {
        "query": "Who is Beelzebul, the twin sister of Baal?",
        "expected_entities": ["ENT_002"],
        "expected_chunks": ["CHK_014", "CHK_015"],
        "category": "Alias"
    },
    {
        "query": "Who is Morax, the God of Contracts?",
        "expected_entities": ["ENT_009"],
        "expected_chunks": ["CHK_022", "CHK_024"],
        "category": "Alias"
    },
    {
        "query": "Who is Barbatos, the God of Freedom?",
        "expected_entities": ["ENT_004"],
        "expected_chunks": ["CHK_022", "CHK_049"],
        "category": "Alias"
    },
    {
        "query": "Who is Lesser Lord Kusanali?",
        "expected_entities": ["ENT_010"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Alias"
    },
    {
        "query": "Who is Rex Lapis of Liyue Harbor?",
        "expected_entities": ["ENT_009", "ENT_006"],
        "expected_chunks": ["CHK_024", "CHK_146"],
        "category": "Alias"
    },
    {
        "query": "Who is the Deity of Eternity in Inazuma?",
        "expected_entities": ["ENT_002", "ENT_008"],
        "expected_chunks": ["CHK_014", "CHK_016"],
        "category": "Alias"
    },
    {
        "query": "Who is the God of Wisdom in Sumeru?",
        "expected_entities": ["ENT_010"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Alias"
    },

    # 3. Multi-hop (7 queries)
    {
        "query": "Who is the successor of Greater Lord Rukkhadevata in Sumeru?",
        "expected_entities": ["ENT_010", "ENT_001"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Multi-hop"
    },
    {
        "query": "How are Ley Lines connected to the Irminsul world tree?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_002", "CHK_005"],
        "category": "Multi-hop"
    },
    {
        "query": "Who did Barbatos meet in Liyue after the Archon War?",
        "expected_entities": ["ENT_004", "ENT_009", "ENT_006"],
        "expected_chunks": ["CHK_022", "CHK_024"],
        "category": "Multi-hop"
    },
    {
        "query": "What is the relationship between the Raiden Shogun and Ei?",
        "expected_entities": ["ENT_002"],
        "expected_chunks": ["CHK_014", "CHK_015"],
        "category": "Multi-hop"
    },
    {
        "query": "What is the connection between Irminsul branches and Prototype Crescent bowstring?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_010", "CHK_002"],
        "category": "Multi-hop"
    },
    {
        "query": "How is the Traveler associated with Mondstadt and Liyue archons?",
        "expected_entities": ["ENT_007", "ENT_004", "ENT_009"],
        "expected_chunks": ["CHK_024", "CHK_049"],
        "category": "Multi-hop"
    },
    {
        "query": "Who is the successorship lineage of Sumeru's world tree protector?",
        "expected_entities": ["ENT_010", "ENT_001"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Multi-hop"
    },

    # 4. Conceptual (7 queries)
    {
        "query": "What is the silver-white tree that grows downwards in the caverns of Teyvat?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_002", "CHK_004"],
        "category": "Conceptual"
    },
    {
        "query": "How does information and memory get added to the repository of Teyvat?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_003", "CHK_005"],
        "category": "Conceptual"
    },
    {
        "query": "What happens when an entire being is removed from Irminsul?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_005", "CHK_006"],
        "category": "Conceptual"
    },
    {
        "query": "What is the concept of eternity in the nation of Thunder?",
        "expected_entities": ["ENT_002", "ENT_008"],
        "expected_chunks": ["CHK_014", "CHK_016"],
        "category": "Conceptual"
    },
    {
        "query": "How does the Akasha terminal gather information from Lesser Lord Kusanali?",
        "expected_entities": ["ENT_010"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Conceptual"
    },
    {
        "query": "What is the Geo Archon's philosophy of contracts in Liyue?",
        "expected_entities": ["ENT_009", "ENT_006"],
        "expected_chunks": ["CHK_024", "CHK_146"],
        "category": "Conceptual"
    },
    {
        "query": "Describe the concept of wind-guided freedom in the Anemo nation.",
        "expected_entities": ["ENT_004", "ENT_003"],
        "expected_chunks": ["CHK_049", "CHK_050"],
        "category": "Conceptual"
    },

    # 5. Hidden Entity (6 queries)
    {
        "query": "What point of interest is located on the eastern side of Dragonspine?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_009", "CHK_2162"],
        "category": "Hidden Entity"
    },
    {
        "query": "What tree was once revered by the ancient city of Sal Vindagnyr?",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_009", "CHK_2163"],
        "category": "Hidden Entity"
    },
    {
        "query": "Where does Albedo conduct his research on Dragonspine?",
        "expected_entities": ["ENT_003"],
        "expected_chunks": ["CHK_1875"],
        "category": "Hidden Entity"
    },
    {
        "query": "Who is the twin sister of Beelzebul that died in Khaenri'ah?",
        "expected_entities": ["ENT_002"],
        "expected_chunks": ["CHK_015", "CHK_021"],
        "category": "Hidden Entity"
    },
    {
        "query": "Who is the Yaksha whose true name is unknown, born 4000 years ago?",
        "expected_entities": ["ENT_006", "ENT_009"],
        "expected_chunks": ["CHK_4493"],
        "category": "Hidden Entity"
    },
    {
        "query": "What was the assembly in Liyue before the Archon War called?",
        "expected_entities": ["ENT_006", "ENT_009"],
        "expected_chunks": ["CHK_2292"],
        "category": "Hidden Entity"
    },

    # 6. Relationship (7 queries)
    {
        "query": "Ei met Venti and Zhongli in Liyue",
        "expected_entities": ["ENT_002", "ENT_004", "ENT_009"],
        "expected_chunks": ["CHK_022", "CHK_024"],
        "category": "Relationship"
    },
    {
        "query": "Venti's relationship with the Traveler in Mondstadt",
        "expected_entities": ["ENT_004", "ENT_007", "ENT_003"],
        "expected_chunks": ["CHK_049", "CHK_050"],
        "category": "Relationship"
    },
    {
        "query": "Zhongli faking his death during the Rite of Descension",
        "expected_entities": ["ENT_009", "ENT_006"],
        "expected_chunks": ["CHK_024", "CHK_146"],
        "category": "Relationship"
    },
    {
        "query": "Nahida and Rukkhadevata successorship link via Irminsul",
        "expected_entities": ["ENT_010", "ENT_001"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Relationship"
    },
    {
        "query": "Morax defeated Chi and Osial in Liyue",
        "expected_entities": ["ENT_009", "ENT_006"],
        "expected_chunks": ["CHK_6826"],
        "category": "Relationship"
    },
    {
        "query": "Albedo and the Traveler research connection",
        "expected_entities": ["ENT_007"],
        "expected_chunks": ["CHK_1875"],
        "category": "Relationship"
    },
    {
        "query": "Raiden Shogun puppet replacement of Ei",
        "expected_entities": ["ENT_002"],
        "expected_chunks": ["CHK_014", "CHK_015"],
        "category": "Relationship"
    },

    # 7. Comparative (6 queries)
    {
        "query": "Compare Venti and Zhongli as archons of Mondstadt and Liyue",
        "expected_entities": ["ENT_004", "ENT_009", "ENT_003", "ENT_006"],
        "expected_chunks": ["CHK_022", "CHK_024"],
        "category": "Comparative"
    },
    {
        "query": "Compare the eternity of Inazuma with the contracts of Liyue",
        "expected_entities": ["ENT_002", "ENT_009", "ENT_008", "ENT_006"],
        "expected_chunks": ["CHK_014", "CHK_024"],
        "category": "Comparative"
    },
    {
        "query": "Compare Lesser Lord Kusanali and Greater Lord Rukkhadevata's rule",
        "expected_entities": ["ENT_010", "ENT_001"],
        "expected_chunks": ["CHK_003", "CHK_004"],
        "category": "Comparative"
    },
    {
        "query": "Compare the Frostbearing Tree and Irminsul world tree functions",
        "expected_entities": ["ENT_001"],
        "expected_chunks": ["CHK_002", "CHK_2163"],
        "category": "Comparative"
    },
    {
        "query": "Compare Furina of Fontaine with Venti of Mondstadt",
        "expected_entities": ["ENT_005", "ENT_004", "ENT_011", "ENT_003"],
        "expected_chunks": ["CHK_050", "CHK_145"],
        "category": "Comparative"
    },
    {
        "query": "Compare Liyue's Archon War and Inazuma's Archon War outcomes",
        "expected_entities": ["ENT_006", "ENT_008", "ENT_009", "ENT_002"],
        "expected_chunks": ["CHK_022", "CHK_3055"],
        "category": "Comparative"
    }
]

os.makedirs("evaluation/retrieval", exist_ok=True)
with open("evaluation/retrieval/ground_truth_large.json", "w") as f:
    json.dump(ground_truth_data, f, indent=2)

print("Generated 50 categorized queries in evaluation/retrieval/ground_truth_large.json")
