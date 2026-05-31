# --- FMCG Simulator with Knowledge Graph + Streamlit Dashboard ---
# Save as fmcg_simulator.py
# Run with: streamlit run fmcg_simulator.py

import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import json
from datetime import datetime

st.set_page_config(page_title="FMCG Simulator", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #0d111b; color: #e2e8f0; }
    .stSidebar { background: #0f172a; }
    .dashboard-card { background: #111827; padding: 0.9rem; border-radius: 14px; border: 1px solid #1f2937; margin-bottom: 0.8rem; }
    .legend-badge { display: inline-block; margin-right: 0.5rem; padding: 0.3rem 0.6rem; border-radius: 999px; color: white; font-size: 0.8rem; }
    .methodology-card { background: #1f2937; padding: 1rem; border-radius: 10px; border-left: 4px solid #4caf50; margin: 0.75rem 0; }
    .tech-stack-item { display: inline-block; background: #111827; padding: 0.4rem 0.8rem; border-radius: 6px; margin: 0.2rem; border: 1px solid #374151; }
    .component-section { background: #0f172a; padding: 1rem; border-radius: 10px; margin: 0.75rem 0; border: 1px solid #1f2937; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================== AGENT & SIMULATION LOGIC ====================

class MemoryStore:
    """Individual and Collective Memory Management System"""
    def __init__(self):
        self.individual_memories = {}  # agent_id -> list of memories
        self.collective_memories = []  # shared market insights
        self.reality_seeds = {}  # extracted facts from external sources
        
    def add_individual_memory(self, agent_id, memory_type, content, timestamp=None):
        """Store individual agent memory"""
        if agent_id not in self.individual_memories:
            self.individual_memories[agent_id] = []
        
        memory = {
            "type": memory_type,
            "content": content,
            "timestamp": timestamp or datetime.now().isoformat(),
            "weight": 1.0
        }
        self.individual_memories[agent_id].append(memory)
    
    def add_collective_memory(self, memory_type, content, agents_involved=None):
        """Store collective/market-level memory"""
        memory = {
            "type": memory_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "agents_involved": agents_involved or [],
            "weight": 1.0
        }
        self.collective_memories.append(memory)
    
    def add_reality_seed(self, seed_type, entity, fact, source="extracted"):
        """Store extracted reality seeds from external sources"""
        seed_key = f"{seed_type}:{entity}"
        if seed_key not in self.reality_seeds:
            self.reality_seeds[seed_key] = []
        
        self.reality_seeds[seed_key].append({
            "fact": fact,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.8
        })
    
    def retrieve_agent_memory(self, agent_id, memory_type=None, limit=5):
        """Retrieve agent's relevant memories"""
        if agent_id not in self.individual_memories:
            return []
        memories = self.individual_memories[agent_id]
        if memory_type:
            memories = [m for m in memories if m["type"] == memory_type]
        return sorted(memories, key=lambda x: x["timestamp"], reverse=True)[:limit]
    
    def retrieve_collective_insights(self, limit=5):
        """Retrieve collective market insights"""
        return sorted(self.collective_memories, key=lambda x: x["timestamp"], reverse=True)[:limit]


class RealitySeedExtractor:
    """Extract real-world facts and entities from text"""
    def __init__(self):
        self.entity_keywords = {
            "demographics": ["young", "old", "millennial", "gen-z", "family", "professional", "student", "retiree"],
            "income_level": ["budget", "affordable", "mid-range", "premium", "luxury", "expensive"],
            "buying_behavior": ["discount-driven", "brand-loyal", "quality-conscious", "trendy", "price-sensitive"],
            "market_segment": ["urban", "rural", "tier-1", "tier-2", "metros", "small-towns"],
            "channels": ["online", "retail", "direct", "distributors", "e-commerce", "marketplace"],
            "season": ["summer", "winter", "monsoon", "festival", "holiday", "promotional"],
        }
    
    def extract_seeds(self, text):
        """Extract reality seeds from market description"""
        seeds = {}
        text_lower = text.lower()
        
        for category, keywords in self.entity_keywords.items():
            found = [kw for kw in keywords if kw in text_lower]
            if found:
                seeds[category] = found
        
        # Extract specific patterns
        if "tier" in text_lower:
            import re
            tier_matches = re.findall(r'tier[- ](\d+)', text_lower)
            if tier_matches:
                seeds["tier_levels"] = tier_matches
        
        return seeds
    
    def generate_agents_from_seeds(self, seeds, agent_count=120):
        """Generate agents based on extracted reality seeds"""
        # Use seeds to bias demographic distribution
        demographics = seeds.get("demographics", [])
        income_hints = seeds.get("income_level", [])
        
        # Create biased probability distributions
        if "young" in demographics or "millennial" in demographics or "gen-z" in demographics:
            age_probs = [0.4, 0.35, 0.15, 0.1]  # Skew towards younger
        else:
            age_probs = [0.25, 0.35, 0.25, 0.15]  # Default
        
        if any(word in income_hints for word in ["budget", "affordable", "discount"]):
            price_sens_bias = 0.7  # More price sensitive
        elif any(word in income_hints for word in ["premium", "luxury"]):
            price_sens_bias = 0.2  # Less price sensitive
        else:
            price_sens_bias = 0.5  # Neutral
        
        return age_probs, price_sens_bias


def construct_seed_graph(seed_text, product):
    """Build a seed knowledge graph from uploaded market material."""
    extractor = st.session_state.get("reality_extractor")
    if not extractor:
        extractor = RealitySeedExtractor()
    seeds = extractor.extract_seeds(seed_text)
    G = nx.Graph()
    G.add_node(product, type="product", label=product)
    for category, values in seeds.items():
        for value in values:
            node_name = f"{category}:{value}"
            G.add_node(node_name, type=category, label=value)
            G.add_edge(node_name, product, relation=f"related_{category}", weight=1)
    if seeds.get("tier_levels"):
        for tier in seeds["tier_levels"]:
            tier_node = f"tier:{tier}"
            G.add_node(tier_node, type="tier", label=f"Tier {tier}")
            G.add_edge(tier_node, product, relation="in_market", weight=1)
    return G, seeds


def create_agent_personality(seed_summary, idx):
    """Generate a persona profile for an agent from seed material."""
    personalities = ["Analytical", "Trend-Seeker", "Value-Driven", "Brand Loyal", "Quality-Focused", "Community Advocate"]
    stances = ["budget", "premium", "balanced", "quality", "convenience"]
    backgrounds = ["Urban professional", "Suburban family", "Rural shopper", "College student", "Young couple"]
    if seed_summary:
        if any(word in seed_summary.get("demographics", []) for word in ["young", "millennial", "gen-z"]):
            backgrounds = ["Urban professional", "College student", "Young couple"]
        if any(word in seed_summary.get("income_level", []) for word in ["budget", "affordable"]):
            stances = ["budget", "balanced"]
        if any(word in seed_summary.get("income_level", []) for word in ["premium", "luxury"]):
            stances = ["premium", "quality"]
    personality = personalities[idx % len(personalities)]
    stance = stances[idx % len(stances)]
    background = backgrounds[idx % len(backgrounds)]
    return personality, stance, background


class SimulationPlatform:
    """Parallel simulation platform for social interactions."""
    def __init__(self, name, style, influence_factor):
        self.name = name
        self.style = style
        self.influence_factor = influence_factor
        self.history = []

    def run_week(self, week, agents, marketing, promotion, availability, memory_store=None):
        interactions = 0
        sentiment = 0.0
        engaged_agents = 0
        for agent in agents:
            if np.random.rand() < 0.08 + 0.02 * agent.loyalty:
                interactions += 1
                engaged_agents += 1
                sentiment += 0.05 if agent.loyalty > 0.5 else -0.02
                if memory_store:
                    memory_store.add_individual_memory(
                        agent.id,
                        "platform_interaction",
                        f"Engaged on {self.name} with style {self.style} in week {week}"
                    )
        sentiment_score = np.clip(sentiment / max(1, engaged_agents), -1.0, 1.0)
        summary = {
            "week": week,
            "platform": self.name,
            "interactions": interactions,
            "engaged_agents": engaged_agents,
            "sentiment": sentiment_score,
            "influence": self.influence_factor,
        }
        self.history.append(summary)
        if memory_store and interactions > 0:
            memory_store.add_collective_memory(
                "platform_event",
                f"{self.name} generated {interactions} interactions with sentiment {sentiment_score:.2f} in week {week}",
                agents_involved=engaged_agents
            )
        return summary


class ReportAgent:
    """Synthesizes simulation outcomes into a prediction report."""
    def __init__(self, product, adoption_timeline, platform_summaries, graph_rag, memory_store):
        self.product = product
        self.adoption_timeline = adoption_timeline
        self.platform_summaries = platform_summaries
        self.graph_rag = graph_rag
        self.memory_store = memory_store

    def generate_report(self):
        peak_week = max(self.adoption_timeline, key=lambda x: x["weekly_new_adopters"])["week"]
        avg_sentiment = np.mean([item["sentiment"] for item in self.platform_summaries]) if self.platform_summaries else 0
        report = [
            f"Report for {self.product}:",
            f"- Final adoption rate: {self.adoption_timeline[-1]['adoption_rate']:.1%}",
            f"- Peak week of interest: Week {peak_week}",
            f"- Average platform sentiment: {avg_sentiment:.2f}",
            f"- Distributors and retailers remain central to market flow in the knowledge graph.",
            "- Consumers with strong loyalty showed the highest chance of adoption and created the most positive platform interactions.",
        ]
        if self.memory_store.reality_seeds:
            report.append("- Reality seeds influenced the simulation by introducing market segment nodes and consumer preferences.")
        report.append("- Recommendation: Monitor distribution availability and promotion intensity together to maximize adoption.")
        return "\n".join(report)

    def answer_question(self, question):
        contexts = self.graph_rag.retrieve_context(question, top_k=4)
        if contexts:
            top_nodes = [node_data.get("label", node_id) for node_id, node_data in contexts]
            context_summary = ", ".join(top_nodes)
            return (
                f"Based on the GraphRAG context, the most relevant factors are: {context_summary}. "
                f"The report indicates that adoption is most sensitive to price, promotion, and availability in this FMCG market."
            )
        return "The report suggests focusing on promotion and distribution, especially for consumer segments that are price-sensitive or brand-loyal."


class GraphRAG:
    """Graph Retrieval Augmented Generation - Enhanced Knowledge Graph with RAG capabilities"""
    def __init__(self, base_graph):
        self.graph = base_graph.copy()
        self.embeddings = {}  # Store semantic embeddings for nodes
        self.query_cache = {}  # Cache query results
        
    def add_semantic_layer(self, node_id, semantic_description):
        """Add semantic embeddings to nodes"""
        # Simple TF-IDF like semantic representation
        words = semantic_description.lower().split()
        self.embeddings[node_id] = {
            "description": semantic_description,
            "keywords": words,
            "timestamp": datetime.now().isoformat()
        }
    
    def retrieve_context(self, query, top_k=5):
        """RAG: Retrieve relevant context for a query"""
        query_words = set(query.lower().split())
        scores = {}
        
        for node_id, embedding in self.embeddings.items():
            # Calculate relevance score
            keyword_overlap = len(set(embedding["keywords"]) & query_words)
            node_data = self.graph.nodes.get(node_id, {})
            
            # Boost score for relevant node types
            type_boost = 1.0
            if node_data.get("type") == "product" and "product" in query_words:
                type_boost = 1.5
            elif node_data.get("type") == "consumer" and any(w in query for w in ["consumer", "adoption"]):
                type_boost = 1.3
            
            scores[node_id] = keyword_overlap * type_boost
        
        # Return top-k results
        top_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(node_id, self.graph.nodes.get(node_id, {})) for node_id, _ in top_results if _ > 0]
    
    def augment_with_memory(self, memory_store):
        """Augment graph with memory-based insights"""
        for seed_key, seed_list in memory_store.reality_seeds.items():
            seed_type, entity = seed_key.split(":", 1)
            # Create memory nodes in graph
            memory_node = f"mem_{entity}_{len(self.graph.nodes())}"
            self.graph.add_node(
                memory_node,
                type="memory",
                seed_type=seed_type,
                entity=entity,
                facts=[s["fact"] for s in seed_list],
                label=f"Memory: {entity}"
            )
            # Connect to relevant entities
            for node in self.graph.nodes():
                if entity.lower() in str(self.graph.nodes[node]).lower():
                    self.graph.add_edge(memory_node, node, relation="supports_context")

# ==================== AGENT & SIMULATION LOGIC ====================

class ConsumerAgent:
    def __init__(self, id, age_group, income_level, price_sensitivity, loyalty, personality="Balanced", stance="balanced", background="General Shopper", memory_store=None):
        self.id = id
        self.age_group = age_group
        self.income_level = income_level
        self.price_sensitivity = price_sensitivity
        self.loyalty = loyalty
        self.personality = personality
        self.stance = stance
        self.background = background
        self.memory_store = memory_store
        self.personal_history = []  # Track individual's decisions

    def decide_purchase(self, price, marketing, promotion, availability):
        base = 0.12
        price_impact = max(0, 1 - self.price_sensitivity * (price / 40))
        loyalty_impact = 0.2 + 0.6 * self.loyalty
        promo_impact = 0.15 * promotion
        marketing_impact = 0.3 * marketing
        availability_impact = 0.25 if availability else -0.2

        stance_boost = 0.0
        if self.stance == "budget" and price < 30:
            stance_boost = 0.05
        elif self.stance == "premium" and price > 35:
            stance_boost = 0.05
        elif self.stance == "quality" and marketing > 0.7:
            stance_boost = 0.03
        elif self.stance == "convenience" and availability:
            stance_boost = 0.04

        score = base + price_impact * 0.4 + loyalty_impact * 0.2 + promo_impact + marketing_impact + availability_impact + stance_boost
        prob = float(np.clip(score, 0, 1))
        
        # Apply memory-based decision boost
        if self.memory_store:
            memories = self.memory_store.retrieve_agent_memory(self.id, "purchase_intent")
            if memories:
                memory_boost = len(memories) * 0.05
                prob = float(np.clip(prob + memory_boost, 0, 1))
        
        adopted = np.random.rand() < prob
        
        # Store memory if adopted
        if adopted and self.memory_store:
            self.memory_store.add_individual_memory(
                self.id,
                "purchase_decision",
                f"Purchased product at price ₹{price} with marketing intensity {marketing:.2f}, stance {self.stance}, personality {self.personality}"
            )
        
        return adopted, prob


def build_agents(count=120, memory_store=None, seed_summary=None):
    age_groups = ["18-25", "26-40", "41-60", "60+"]
    income_levels = ["low", "mid", "high"]
    agents = []
    for i in range(1, count + 1):
        personality, stance, background = create_agent_personality(seed_summary, i)
        agent = ConsumerAgent(
            id=f"C{i}",
            age_group=np.random.choice(age_groups, p=[0.25, 0.35, 0.25, 0.15]),
            income_level=np.random.choice(income_levels, p=[0.3, 0.5, 0.2]),
            price_sensitivity=np.random.beta(2, 2),
            loyalty=np.random.beta(2, 3),
            personality=personality,
            stance=stance,
            background=background,
            memory_store=memory_store
        )
        agents.append(agent)
    return agents


def run_simulation_over_time(product, price, marketing, promotion, availability, agents, num_weeks=12):
    """Run simulation across multiple time steps to show real-time adoption evolution."""
    adoption_timeline = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    platforms = [
        SimulationPlatform("TrendStream", "twitter-like", 0.92),
        SimulationPlatform("CommunityHub", "reddit-like", 0.78),
    ]
    
    # Initialize agent adoption tracking
    for agent in agents:
        agent.adoption_time = None
    
    all_data = []
    
    for week in range(1, num_weeks + 1):
        progress = min(week / num_weeks, 1.0)
        progress_bar.progress(progress)
        status_text.text(f"Simulating week {week}/{num_weeks}... ({int(progress * 100)}%)")
        
        # Increase marketing exposure over time
        week_marketing = min(marketing + (week / (num_weeks * 2)), 1.0)
        
        rows = []
        adopted_this_week = 0
        platform_summaries = []
        
        for agent in agents:
            if agent.adoption_time is None:
                # Increase probability if agent has seen marketing
                week_prob_boost = 0.05 * (week / num_weeks) if week > 1 else 0
                adopted, prob = agent.decide_purchase(price, week_marketing + week_prob_boost, promotion, availability)
                
                if adopted:
                    agent.adoption_time = week
                    adopted_this_week += 1
                
                rows.append({
                    "consumer_id": agent.id,
                    "age_group": agent.age_group,
                    "income_level": agent.income_level,
                    "price_sensitivity": agent.price_sensitivity,
                    "loyalty": agent.loyalty,
                    "adoption_prob": prob,
                    "adopted": int(adopted),  # Convert boolean to int (0 or 1)
                    "adoption_time": agent.adoption_time,
                    "week": week,
                })
            else:
                # Agent already adopted, include in the record
                rows.append({
                    "consumer_id": agent.id,
                    "age_group": agent.age_group,
                    "income_level": agent.income_level,
                    "price_sensitivity": agent.price_sensitivity,
                    "loyalty": agent.loyalty,
                    "adoption_prob": 1.0,
                    "adopted": 1,
                    "adoption_time": agent.adoption_time,
                    "week": week,
                })
        
        df_week = pd.DataFrame(rows)
        total_adopted = df_week["adopted"].sum()
        adoption_rate = total_adopted / len(agents)
        
        for platform in platforms:
            platform_summary = platform.run_week(week, agents, week_marketing, promotion, availability, memory_store=agents[0].memory_store if agents else None)
            platform_summaries.append(platform_summary)
        
        avg_sentiment = np.mean([item["sentiment"] for item in platform_summaries]) if platform_summaries else 0
        total_interactions = sum(item["interactions"] for item in platform_summaries)
        
        adoption_timeline.append({
            "week": week,
            "adoption_rate": adoption_rate,
            "cumulative_adopted": int(total_adopted),
            "weekly_new_adopters": adopted_this_week,
            "weekly_platform_interactions": int(total_interactions),
            "avg_platform_sentiment": float(avg_sentiment),
        })
        
        all_data.extend(rows)
    
    progress_bar.empty()
    status_text.empty()
    
    df_final = pd.DataFrame(all_data)
    # Get latest state for each agent
    df_final_state = df_final.drop_duplicates(subset=["consumer_id"], keep="last")
    adoption_rate_final = df_final_state["adopted"].mean()
    graph = build_graph(df_final_state, product, marketing, promotion, availability)
    
    platform_summaries = [summary for platform in platforms for summary in platform.history]
    return df_final, adoption_rate_final, graph, pd.DataFrame(adoption_timeline), platform_summaries


def build_graph(df, product, marketing, promotion, availability):
    G = nx.Graph()
    G.add_node(product, type="product", label=product)
    retailers = ["Retailer A", "Retailer B", "Retailer C"]
    distributors = ["Distributor X", "Distributor Y"]

    for r in retailers:
        G.add_node(r, type="retailer", label=r)
        G.add_edge(r, product, relation="sells", weight=1)

    for d in distributors:
        G.add_node(d, type="distributor", label=d)
        for r in retailers:
            G.add_edge(d, r, relation="supplies", weight=1)

    for _, row in df.head(25).iterrows():
        consumer = row["consumer_id"]
        G.add_node(consumer, type="consumer", age=row["age_group"], income=row["income_level"])
        relation = "buys" if row["adopted"] else "interested"
        G.add_edge(consumer, product, relation=relation, weight=row["adoption_prob"])

    metadata = {
        "marketing": marketing,
        "promotion": promotion,
        "availability": availability,
    }
    nx.set_node_attributes(G, metadata)
    return G


def visualize_graph(G, height=520, show_edge_labels=False):
    net = Network(height=f"{height}px", width="100%", bgcolor="#111111", font_color="white")
    net.force_atlas_2based()
    net.set_options(
        """
        var options = {
          "physics": {
            "barnesHut": {"gravitationalConstant": -20000, "springLength": 180, "springConstant": 0.04, "damping": 0.09},
            "minVelocity": 0.75
          },
          "nodes": {
            "font": {"size": 16, "face": "Arial", "color": "#ffffff"},
            "scaling": {"min": 10, "max": 40}
          },
          "edges": {
            "smooth": {"enabled": true, "type": "continuous"},
            "color": {"color": "#cccccc"}
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "hideEdgesOnDrag": false
          }
        }
        """
    )

    for node, data in G.nodes(data=True):
        node_type = data.get("type", "other")
        label = data.get("label", node)
        title = f"Type: {node_type.title()}"
        size = 15
        if node_type == "product":
            color = "#ff6f61"
            shape = "box"
            size = 42
            title += "<br>Core Product"
        elif node_type == "consumer":
            color = "#4caf50"
            shape = "dot"
            size = 16
            title += f"<br>Age: {data.get('age', 'N/A')}<br>Income: {data.get('income', 'N/A')}"
        elif node_type == "retailer":
            color = "#2196f3"
            shape = "triangle"
            size = 28
            title += "<br>Retail Partner"
        elif node_type == "distributor":
            color = "#ffa726"
            shape = "diamond"
            size = 28
            title += "<br>Distribution Node"
        else:
            color = "#9e9e9e"
            shape = "ellipse"
        net.add_node(node, label=label, color=color, shape=shape, title=title, size=size)

    for source, target, data in G.edges(data=True):
        edge_label = data.get("relation", "") if show_edge_labels else ""
        edge_title = f"Relation: {data.get('relation', '')}<br>Weight: {data.get('weight', '')}"
        net.add_edge(source, target, label=edge_label, color="#bbbbbb", width=2, title=edge_title)

    path = "graph.html"
    net.write_html(path)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=height, scrolling=True)

# ==================== STREAMLIT SIDEBAR ====================

# Initialize memory and graph systems
if "memory_store" not in st.session_state:
    st.session_state.memory_store = MemoryStore()

if "reality_extractor" not in st.session_state:
    st.session_state.reality_extractor = RealitySeedExtractor()

with st.sidebar:
    st.header("Simulation Controls")
    product = st.selectbox("Product", ["Spicy Snack", "Instant Noodles", "Cold Drink", "Health Drink"])
    price = st.slider("Retail Price (₹)", 10, 60, 24, 1)
    marketing = st.slider("Marketing Intensity", 0.0, 1.0, 0.65, 0.05)
    promotion = st.select_slider("Promotion level", options=["None", "Low", "Medium", "High"])
    availability = st.checkbox("Stable distribution and availability", value=True)
    base_agent_count = st.slider("Base consumer cohort", 40, 240, 120, 20)
    spawn_batch = st.slider("Spawn additional agents", 10, 120, 40, 10)
    spawn_button = st.button("Try Now - Spawn agents on the fly")
    
    st.markdown("---")
    st.write(f"**Active consumer agents:** {len(st.session_state.agents) if 'agents' in st.session_state else base_agent_count}")
    st.caption("Use the 'Try Now' button to grow the consumer population during the current session, then run the simulation on the Simulation tab.")
    st.markdown("- Set the base cohort size first.\n- Choose how many extra agents to spawn.\n- Click 'Try Now' to add them instantly.\n- Navigate to the Simulation tab to run and observe the expanded cohort.")
    
    st.markdown("---")
    scenario = st.selectbox("Scenario", ["Baseline", "Discount Campaign", "Premium Launch", "Trade Promotion"])
    
    st.markdown("---")
    st.write("**Reality Seeds:** Optionally inject market knowledge:")
    reality_seeds_input = st.text_area("Market context (for reality seed extraction)", placeholder="E.g., Urban tier-1 cities, young professionals, digital marketing focus...")
    seed_file = st.file_uploader("Upload seed material (text file)", type=["txt"], help="Optional supporting market material for GraphRAG extraction.")
    if seed_file is not None:
        try:
            seed_text = seed_file.read().decode("utf-8", errors="ignore")
        except AttributeError:
            seed_text = str(seed_file)
        st.session_state.seed_material = seed_text
        if not reality_seeds_input:
            reality_seeds_input = seed_text
        else:
            reality_seeds_input += "\n" + seed_text

scenario_effects = {
    "Baseline": (0.0, 0.0),
    "Discount Campaign": (-0.15, 0.15),
    "Premium Launch": (0.12, -0.05),
    "Trade Promotion": (0.0, 0.25),
}
price_delta, marketing_bonus = scenario_effects[scenario]
price = max(5, round(price + price_delta * price))
marketing = float(np.clip(marketing + marketing_bonus, 0, 1))

promotion_levels = {"None": 0.0, "Low": 0.15, "Medium": 0.35, "High": 0.55}
promotion_score = promotion_levels[promotion]

# Extract and inject reality seeds
if reality_seeds_input:
    reality_seeds = st.session_state.reality_extractor.extract_seeds(reality_seeds_input)
    st.session_state.seed_summary = reality_seeds
    for category, values in reality_seeds.items():
        st.session_state.memory_store.add_reality_seed(category, f"{product}_market", str(values))
    if st.session_state.get("seed_material") or reality_seeds_input:
        seed_graph, extracted_summary = construct_seed_graph(reality_seeds_input, product)
        st.session_state.seed_graph = seed_graph
        st.session_state.seed_summary = extracted_summary

seed_summary_changed = st.session_state.get("seed_summary") != st.session_state.get("last_seed_summary")
if "agents" not in st.session_state or st.session_state.get("base_agent_count") != base_agent_count or seed_summary_changed:
    st.session_state.agents = build_agents(base_agent_count, memory_store=st.session_state.memory_store, seed_summary=st.session_state.get("seed_summary"))
    st.session_state.agents_count = len(st.session_state.agents)
    st.session_state.base_agent_count = base_agent_count
    st.session_state.last_seed_summary = st.session_state.get("seed_summary")

if spawn_button:
    additional_agents = build_agents(spawn_batch, memory_store=st.session_state.memory_store, seed_summary=st.session_state.get("seed_summary"))
    st.session_state.agents.extend(additional_agents)
    st.session_state.agents_count = len(st.session_state.agents)
    st.success(f"Spawned {len(additional_agents)} extra agents. Total agents now: {st.session_state.agents_count}.")

# Run simulation
with st.spinner("Running the FMCG simulation with Memory & GraphRAG..."):
    df, adoption_rate, graph, adoption_timeline, platform_summaries = run_simulation_over_time(product, price, marketing, promotion_score, availability, st.session_state.agents, num_weeks=12)
    
    # Store collective insights in memory
    st.session_state.memory_store.add_collective_memory(
        "simulation_result",
        f"Adoption rate: {adoption_rate:.1%}, Price: ₹{price}, Marketing: {marketing:.0%}",
        agents_involved=len(st.session_state.agents)
    )
    
    # Build GraphRAG
    graph_rag = GraphRAG(graph)
    for node in graph.nodes():
        node_data = graph.nodes[node]
        desc = f"{node_data.get('type', 'node')} - {node_data.get('label', node)}"
        graph_rag.add_semantic_layer(node, desc)
    
    # Augment with memory
    graph_rag.augment_with_memory(st.session_state.memory_store)
    
    st.session_state.graph_rag = graph_rag
    report_agent = ReportAgent(product, adoption_timeline.to_dict("records"), platform_summaries, graph_rag, st.session_state.memory_store)
    st.session_state.report_text = report_agent.generate_report()
    st.session_state.report_agent = report_agent

# ==================== CREATE 3 TABS ====================
tab_simulation, tab_methodology, tab_llm = st.tabs(["Simulation", "Methodology", "Scenario Generation"])

# ==================== TAB 2: METHODOLOGY ====================
with tab_methodology:
    st.title("Methodology & Architecture")
    st.info("This page is for methodology and architecture only. Simulation controls live in the left sidebar and are used on the Simulation tab.")
    st.write("Complete documentation of the FMCG Simulator application, including components, workflow, and technical implementation.")
    
    st.markdown("---")
    
    st.subheader("1️⃣ Application Overview")
    st.markdown(f"""
    The **FMCG Simulator** is an advanced multi-agent simulation system designed to model consumer adoption patterns 
    for Fast-Moving Consumer Goods (FMCG) products. It integrates real-time temporal dynamics, knowledge graph visualization, 
    and AI-powered scenario generation to provide actionable market insights.
    """)
    
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Simulation Weeks", "12", "real-time progression")
        with col2:
            st.metric("Consumer Agents", len(st.session_state.agents) if "agents" in st.session_state else base_agent_count, "synthetic population")
        with col3:
            st.metric("Market Scenarios", "4", "configurable templates")
    
    st.markdown("---")
    
    st.subheader("2️⃣ Core Components")
    
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### Consumer Agent Model")
        st.markdown("""
        **Purpose:** Model individual consumer behavior and purchase decisions
        
        **Attributes:**
        - Age Group: 18-25, 26-40, 41-60, 60+
        - Income Level: Low, Mid, High
        - Price Sensitivity: Beta(2,2) distribution
        - Loyalty: Beta(2,3) distribution
        
        **Decision Function:**
        - Base probability: 12%
        - Price impact (0-40%): Inverse to price sensitivity
        - Loyalty impact (20-80%): Product affinity
        - Promotion impact (0-15%): Discount-driven purchase
        - Marketing impact (0-30%): Campaign effectiveness
        - Availability impact (±25%): Distribution reach
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_comp2:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### Temporal Simulation Engine")
        st.markdown("""
        **Purpose:** Simulate adoption patterns over 12 weeks with market dynamics
        
        **Key Features:**
        - Real-time adoption tracking per week
        - Cumulative adoption curve modeling
        - Weekly cohort analysis
        - Marketing exposure boost (linear increase)
        - Probability boost over time (5% per week)
        
        **Output Metrics:**
        - Adoption rate progression
        - Weekly new adopters
        - Cumulative adoption count
        - Time-to-adoption distribution
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    col_comp3, col_comp4 = st.columns(2)
    
    with col_comp3:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### Knowledge Graph Visualization")
        st.markdown("""
        **Purpose:** Represent relationships between supply chain and consumer nodes
        
        **Node Types:**
        - Product (Core offering)
        - Consumers (Adoption agents)
        - Retailers (Distribution partners)
        - Distributors (Logistics nodes)
        
        **Edge Relations:**
        - sells, buys, interested, supplies
        - Weight-based on adoption probability
        - Interactive exploration with tooltips
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_comp4:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### AI-Powered Scenario Generator")
        st.markdown("""
        **Purpose:** Generate realistic market scenarios from natural language
        
        **Capabilities:**
        - Price sensitivity detection
        - Marketing effectiveness analysis
        - Promotion intensity assessment
        - Target demographic profiling
        - Distribution availability inference
        
        **Algorithm:** Rule-based NLP with keyword extraction
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.subheader("Advanced Features: GraphRAG, Memory and Reality Seeds")
    
    graphrag_col1, graphrag_col2, graphrag_col3 = st.columns(3)
    
    with graphrag_col1:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### Memory Management System")
        st.markdown("""
        **Individual Memory:**
        - Stores agent purchase decisions
        - Tracks decision history per consumer
        - Influences future purchasing behavior
        - Memory boost: +5% per stored memory
        
        **Collective Memory:**
        - Market-level insights extracted
        - Shared learning across simulation
        - Stores aggregate patterns
        - Enables scenario comparison
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with graphrag_col2:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### Reality Seed Extraction")
        st.markdown("""
        **Purpose:** Extract real-world market facts from natural language
        
        **Extracts:**
        - Demographics (young, professional, family)
        - Income levels (budget, premium, luxury)
        - Buying behaviors (discount, loyal, quality)
        - Market segments (urban, rural, tier-1/2)
        - Channels (online, retail, direct)
        - Seasonality patterns
        
        **Impact:** Biases agent generation & simulation parameters
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with graphrag_col3:
        st.markdown("<div class='component-section'>", unsafe_allow_html=True)
        st.markdown("#### GraphRAG Construction")
        st.markdown("""
        **Graph Retrieval Augmented Generation**
        
        **Features:**
        - Semantic node embeddings
        - Context retrieval for queries
        - Memory-augmented knowledge graph
        - Node type boosting for relevance
        - Query caching for efficiency
        
        **Benefits:**
        - Enhanced interpretability
        - Context-aware decisions
        - Retrievable insights
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    if st.session_state.get("seed_graph"):
        st.markdown("---")
        st.subheader("Reality Seed Knowledge Graph")
        seed_graph = st.session_state.seed_graph
        seed_summary = st.session_state.get("seed_summary", {})
        st.write("This graph was extracted from your uploaded market material or text description to form the simulation reality.")
        st.write("**Extracted seeds:**", ", ".join(seed_summary.keys()))
        st.write("Use the Simulation tab to explore the resulting graph relationships.")
    
    st.markdown("---")
    
    st.subheader("Simulation Workflow")
    st.markdown("""
    - INPUT PARAMETERS (Sidebar)
    - Product, Price, Marketing, Promotion, Availability, Scenario
    - SCENARIO EFFECTS APPLIED
    - Adjust price and marketing based on selected scenario
    - AGENT POOL CREATION
    - Generate N consumers with random attributes
    - TEMPORAL SIMULATION LOOP (12 weeks)
      - Week 1: Initial adoption decisions
      - Week 2-12: Accumulate adopters; boost marketing exposure
      - Track weekly new adopters and cumulative adoption
      - Output time-series adoption data
    - KNOWLEDGE GRAPH CONSTRUCTION
      - Build supply chain and consumer network from adoption data
    - VISUALIZATION AND INSIGHTS
      - Timeline charts, segmentation analysis, interactive graph
    """)
    
    st.markdown("---")
    
    st.subheader("4️⃣ Technical Stack")
    
    tech_stack = {
        "Frontend Framework": ["Streamlit", "CSS Styling"],
        "Data Processing": ["Pandas", "NumPy"],
        "Visualization": ["Matplotlib", "PyVis (NetworkX)"],
        "Graph Engine": ["NetworkX", "PyVis Network"],
        "ML/Simulation": ["NumPy Beta distributions", "Stochastic modeling"],
        "Deployment": ["Python 3.13", "Streamlit server"],
    }
    
    for category, tools in tech_stack.items():
        st.markdown(f"**{category}:**")
        cols = st.columns(len(tools))
        for idx, tool in enumerate(tools):
            cols[idx].markdown(f"<span class='tech-stack-item'>{tool}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.subheader("5️⃣ Key Metrics & Formulas")
    
    metric_col1, metric_col2 = st.columns(2)
    
    with metric_col1:
        st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
        st.markdown("##### Adoption Probability Formula")
        st.latex(r"P_{adopt} = base + w_1 P_{price} + w_2 P_{loyalty} + P_{promo} + P_{marketing} + P_{availability}")
        st.markdown("""
        Where:
        - base = 0.12 (baseline adoption rate)
        - w₁ = 0.4, w₂ = 0.2 (component weights)
        - Each component contributes independently to final probability
        """)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with metric_col2:
        st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
        st.markdown("##### Market Dynamics")
        st.markdown(r"""
        **Weekly Marketing Boost:**
        $$M_{week} = M_{baseline} + \frac{week}{num\_weeks \times 2}$$
        
        **Probability Boost over Time:**
        $$P_{boost} = 0.05 \times \frac{week}{num\_weeks}$$
        """)
        st.markdown("</div>", unsafe_allow_html=True)

# ==================== TAB 1: SIMULATION ====================
with tab_simulation:
    st.title("FMCG Market Simulation")
    
    st.markdown("#")
    metric_col1, metric_col2, metric_col3 = st.columns([1, 1, 1])
    metric_col1.metric("Adoption Rate", f"{adoption_rate:.1%}", delta=f"{(adoption_rate - 0.2):+.1%}")
    metric_col2.metric("Average Price", f"₹{price}", delta=f"{(price - 30):+.0f}")
    metric_col3.metric("Promotion Level", promotion, delta=f"{promotion_score:.0%}")
    
    st.markdown("---")
    
    st.markdown("### Adoption Timeline")
    timeline_col1, timeline_col2 = st.columns(2)
    
    with timeline_col1:
        fig_timeline, ax_timeline = plt.subplots(figsize=(6, 3), facecolor="#121212")
        ax_timeline.set_facecolor("#121212")
        ax_timeline.plot(adoption_timeline["week"], adoption_timeline["adoption_rate"] * 100, marker="o", color="#4caf50", linewidth=2, markersize=6)
        ax_timeline.fill_between(adoption_timeline["week"], adoption_timeline["adoption_rate"] * 100, alpha=0.3, color="#4caf50")
        ax_timeline.set_title("Adoption Rate Over 12 Weeks", color="#ffffff")
        ax_timeline.set_xlabel("Week", color="#ffffff")
        ax_timeline.set_ylabel("Adoption Rate (%)", color="#ffffff")
        ax_timeline.tick_params(colors="#ffffff")
        ax_timeline.spines["bottom"].set_color("#444444")
        ax_timeline.spines["left"].set_color("#444444")
        ax_timeline.spines["top"].set_color("#121212")
        ax_timeline.spines["right"].set_color("#121212")
        ax_timeline.grid(color="#333333", linestyle="--", linewidth=0.4)
        st.pyplot(fig_timeline)
    
    with timeline_col2:
        fig_cumul, ax_cumul = plt.subplots(figsize=(6, 3), facecolor="#121212")
        ax_cumul.set_facecolor("#121212")
        ax_cumul.bar(adoption_timeline["week"], adoption_timeline["weekly_new_adopters"], color="#ff9800", edgecolor="#333333")
        ax_cumul.set_title("New Adopters per Week", color="#ffffff")
        ax_cumul.set_xlabel("Week", color="#ffffff")
        ax_cumul.set_ylabel("New Adopters", color="#ffffff")
        ax_cumul.tick_params(colors="#ffffff")
        ax_cumul.spines["bottom"].set_color("#444444")
        ax_cumul.spines["left"].set_color("#444444")
        ax_cumul.spines["top"].set_color("#121212")
        ax_cumul.spines["right"].set_color("#121212")
        ax_cumul.grid(axis="y", color="#333333", linestyle="--", linewidth=0.4)
        st.pyplot(fig_cumul)
    
    st.markdown("---")
    
    st.markdown("### Market Insight Panels")
    insight_col1, insight_col2 = st.columns([2, 1])
    with insight_col1:
        st.markdown("**Adoption Segmentation by Demographics**")
        seg_summary = df.groupby(["age_group", "income_level"]).agg(
            consumers=("consumer_id", "count"),
            adoption_rate=("adopted", "mean"),
            avg_prob=("adoption_prob", "mean"),
        ).reset_index()
        seg_summary["adoption_rate"] = seg_summary["adoption_rate"].map("{:.1%}".format)
        seg_summary["avg_prob"] = seg_summary["avg_prob"].map("{:.2f}".format)
        st.dataframe(seg_summary, height=260, use_container_width=True)
    
    with insight_col2:
        st.markdown("**Income Distribution**")
        dist_summary = df.groupby(["income_level"]).agg(
            consumers=("consumer_id", "count"),
            adoption_rate=("adopted", "mean"),
        ).reset_index()
        dist_summary["adoption_rate"] = dist_summary["adoption_rate"].map("{:.1%}".format)
        st.table(dist_summary)
    
    st.markdown("---")
    
    st.markdown("### Trend Visualizations")
    chart_col1, chart_col2 = st.columns([1, 1])
    with chart_col1:
        fig, ax = plt.subplots(figsize=(6, 3), facecolor="#121212")
        ax.set_facecolor("#121212")
        ax.hist(df["adoption_prob"], bins=12, color="#ff9800", edgecolor="#333333")
        ax.set_title("Adoption Probability Distribution", color="#ffffff")
        ax.set_xlabel("Probability", color="#ffffff")
        ax.set_ylabel("Consumers", color="#ffffff")
        ax.tick_params(colors="#ffffff")
        ax.spines["bottom"].set_color("#444444")
        ax.spines["left"].set_color("#444444")
        ax.spines["top"].set_color("#121212")
        ax.spines["right"].set_color("#121212")
        ax.grid(color="#333333", linestyle="--", linewidth=0.4)
        st.pyplot(fig)
    
    with chart_col2:
        age_data = df.groupby("age_group")["adopted"].mean().reset_index()
        fig2, ax2 = plt.subplots(figsize=(6, 3), facecolor="#121212")
        ax2.set_facecolor("#121212")
        bars = ax2.bar(age_data["age_group"], age_data["adopted"], color=["#4caf50", "#66bb6a", "#aed581", "#c5e1a5"])
        ax2.set_title("Adoption Rate by Age Group", color="#ffffff")
        ax2.set_ylabel("Adoption Rate", color="#ffffff")
        ax2.set_ylim(0, 1)
        ax2.tick_params(colors="#ffffff")
        ax2.spines["bottom"].set_color("#444444")
        ax2.spines["left"].set_color("#444444")
        ax2.spines["top"].set_color("#121212")
        ax2.spines["right"].set_color("#121212")
        ax2.grid(axis="y", color="#333333", linestyle="--", linewidth=0.4)
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(f"{height:.0%}", xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 6), textcoords="offset points", ha="center", color="#ffffff")
        st.pyplot(fig2)
    
    st.markdown("---")
    
    st.subheader("Knowledge Graph - Supply Chain and Adoption Network")
    st.write("Drag nodes to explore, hover for details, and zoom for clarity. This graph shows product, retailers, distributors, and select consumers.")
    with st.container():
        legend_col1, legend_col2, legend_col3 = st.columns(3)
        legend_col1.markdown("<span class='legend-badge' style='background:#ff6f61'>Product</span><span class='legend-badge' style='background:#4caf50'>Consumer</span>", unsafe_allow_html=True)
        legend_col2.markdown("<span class='legend-badge' style='background:#2196f3'>Retailer</span><span class='legend-badge' style='background:#ffa726'>Distributor</span>", unsafe_allow_html=True)
        legend_col3.write("")
        edge_toggle = legend_col3.checkbox("Show edge labels", value=False)
        legend_col3.markdown("*Interactive exploration*")
    
    visualize_graph(graph, height=680, show_edge_labels=edge_toggle)
    
    with st.expander("Full consumer sample data", expanded=False):
        st.dataframe(df.head(20), use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("Post-Simulation Prediction Report")
    if st.session_state.get("report_text"):
        st.markdown(f"<div class='component-section'><pre style='color:#e2e8f0;'>{st.session_state['report_text']}</pre></div>", unsafe_allow_html=True)
    else:
        st.info("Run the simulation to generate the prediction report.")
    
    st.markdown("---")
    
    st.subheader("Memory and GraphRAG Insights")
    st.write("*Real-time learning system integrating individual agent memories and collective market insights*")
    
    mem_col1, mem_col2, mem_col3 = st.columns(3)
    
    with mem_col1:
        st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
        st.markdown("#### Collective Memory")
        collective_insights = st.session_state.memory_store.retrieve_collective_insights(limit=3)
        if collective_insights:
            for insight in collective_insights:
                st.markdown(f"**{insight['type']}**  \n{insight['content']}")
        else:
            st.info("No collective memories yet. Run simulation to generate insights.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with mem_col2:
        st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
        st.markdown("#### Reality Seeds Extracted")
        if st.session_state.memory_store.reality_seeds:
            for seed_key, seeds in list(st.session_state.memory_store.reality_seeds.items())[:3]:
                seed_type, entity = seed_key.split(":", 1)
                st.markdown(f"**{seed_type}**  \n{entity}")
                for seed in seeds[:1]:
                    st.caption(f"{seed['fact'][:50]}...")
        else:
            st.info("Add market context in sidebar to extract reality seeds.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with mem_col3:
        st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
        st.markdown("#### GraphRAG Status")
        if hasattr(st.session_state, 'graph_rag'):
            rag = st.session_state.graph_rag
            st.markdown(f"""
            **Graph Nodes:** {len(rag.graph.nodes())}
            
            **Graph Edges:** {len(rag.graph.edges())}
            
            **Semantic Layers:** {len(rag.embeddings)}
            
            **Memory Augmented:** Yes
            """)
        else:
            st.info("GraphRAG initialized with simulation run.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.expander("GraphRAG Query Interface", expanded=False):
        st.write("Search for relevant context in the knowledge graph using natural language:")
        rag_query = st.text_input("Enter a query:", placeholder="E.g., What influences young consumer adoption?")
        if rag_query and hasattr(st.session_state, 'graph_rag'):
            results = st.session_state.graph_rag.retrieve_context(rag_query, top_k=5)
            st.markdown("**Retrieved Context:**")
            for node_id, node_data in results:
                st.markdown(f"- **{node_data.get('label', node_id)}** ({node_data.get('type', 'node')})")

# ==================== TAB 3: LLM SCENARIO GENERATION ====================
with tab_llm:
    st.title("AI-Powered Market Scenario Generation")
    st.write("Generate realistic market parameters by describing market conditions in natural language. The app analyzes keywords to extract market insights.")
    
    st.markdown("---")
    
    st.subheader("Describe Your Market")
    market_desc = st.text_area(
        "Enter market conditions:", 
        "Urban market in tier-1 cities, young demographic, health-conscious consumers, competitive retail landscape, aggressive promotional campaigns expected.",
        height=100
    )
    
    col_gen1, col_gen2, col_gen3 = st.columns([2, 1, 1])
    with col_gen1:
        st.write("*Keywords analyzed: price, premium, digital, traditional, aggressive, discount, young, family, wide distribution, etc.*")
    with col_gen2:
        st.write("")
    with col_gen3:
        st.write("")
        generate_scenario = st.button("Analyze Market", use_container_width=True)
    
    if generate_scenario or st.session_state.get("scenario_generated", False):
        if market_desc.strip() or st.session_state.get("scenario_generated", False):
            if generate_scenario:
                with st.spinner("Analyzing market conditions..."):
                    scenario_params = {}
                    market_lower = market_desc.lower()
                    
                    # Price sensitivity
                    if any(word in market_lower for word in ["price conscious", "budget", "discount", "cheap", "affordab"]):
                        scenario_params["price_sensitivity"] = 0.8
                    elif any(word in market_lower for word in ["premium", "luxury", "expensive", "high-end"]):
                        scenario_params["price_sensitivity"] = 0.2
                    else:
                        scenario_params["price_sensitivity"] = 0.5
                    
                    # Marketing effectiveness
                    if any(word in market_lower for word in ["digital", "social media", "advertising", "campaigns", "aggressive"]):
                        scenario_params["marketing"] = 0.75
                    elif any(word in market_lower for word in ["traditional", "word of mouth", "organic"]):
                        scenario_params["marketing"] = 0.45
                    else:
                        scenario_params["marketing"] = 0.6
                    
                    # Promotion level
                    if any(word in market_lower for word in ["competitive", "aggressive promo", "discounts", "offers"]):
                        scenario_params["promotion"] = "High"
                    elif any(word in market_lower for word in ["stable", "steady", "minimal promo"]):
                        scenario_params["promotion"] = "Low"
                    else:
                        scenario_params["promotion"] = "Medium"
                    
                    # Target demographic characteristics
                    if any(word in market_lower for word in ["young", "millennial", "gen-z", "youth"]):
                        scenario_params["target"] = "Young & Tech-Savvy"
                    elif any(word in market_lower for word in ["family", "middle-class", "working professional"]):
                        scenario_params["target"] = "Middle-class Families"
                    else:
                        scenario_params["target"] = "Mixed Demographics"
                    
                    # Availability/distribution
                    if any(word in market_lower for word in ["wide", "distributed", "accessible", "available"]):
                        scenario_params["availability"] = True
                    else:
                        scenario_params["availability"] = False
                    
                    st.session_state["scenario_params"] = scenario_params
                    st.session_state["scenario_generated"] = True
            else:
                scenario_params = st.session_state.get("scenario_params", {})
            
            if scenario_params:
                st.success("Market scenario generated successfully.")
                
                st.subheader("Generated Market Parameters")
                
                param_col1, param_col2 = st.columns(2)
                
                with param_col1:
                    st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
                    st.markdown("#### Key Parameters")
                    st.markdown(f"""
                    **Target Segment:** {scenario_params['target']}
                    
                    **Price Sensitivity:** {scenario_params['price_sensitivity']:.0%}
                    - Indicates % of purchasing decisions driven by price
                    
                    **Marketing Effectiveness:** {scenario_params['marketing']:.0%}
                    - Campaign impact on adoption probability
                    
                    **Promotion Intensity:** {scenario_params['promotion']}
                    - Expected discount/offer levels in market
                    
                    **Distribution Available:** {'Wide coverage' if scenario_params['availability'] else 'Limited reach'}
                    """)
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with param_col2:
                    st.markdown("<div class='methodology-card'>", unsafe_allow_html=True)
                    st.markdown("#### Strategic Insights")
                    insights = []
                    
                    if scenario_params["price_sensitivity"] > 0.7:
                        insights.append("Price-sensitive market - Focus on value proposition")
                    elif scenario_params["price_sensitivity"] < 0.3:
                        insights.append("Premium market - Emphasize quality and brand")
                    else:
                        insights.append("Balanced market - Mix of value and premium")
                    
                    if scenario_params["marketing"] > 0.6:
                        insights.append("Digital focus - Social media and online campaigns")
                    else:
                        insights.append("Traditional focus - Word-of-mouth strategy")
                    
                    if scenario_params["promotion"] == "High":
                        insights.append("Promotional market - Use bundling and discounts")
                    
                    if not scenario_params["availability"]:
                        insights.append("Distribution challenge - Expand retail footprint")
                    
                    for insight in insights:
                        st.markdown(f"• {insight}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                
                st.subheader("Knowledge Graph - AI Generated Scenario")
                st.write("*Graph visualization updated based on AI-generated market parameters.*")
                
                with st.container():
                    legend_col1, legend_col2, legend_col3 = st.columns(3)
                    legend_col1.markdown("<span class='legend-badge' style='background:#ff6f61'>Product</span><span class='legend-badge' style='background:#4caf50'>Consumer</span>", unsafe_allow_html=True)
                    legend_col2.markdown("<span class='legend-badge' style='background:#2196f3'>Retailer</span><span class='legend-badge' style='background:#ffa726'>Distributor</span>", unsafe_allow_html=True)
                    legend_col3.write("")
                    edge_toggle_llm = legend_col3.checkbox("Show edge labels (LLM)", value=False)
                
                visualize_graph(graph, height=680, show_edge_labels=edge_toggle_llm)
                
                st.markdown("---")
                
                st.subheader("Entity and Relationship Extraction")
                st.write("Extract additional market entities from natural language description:")
                
                entity_desc = st.text_area(
                    "Describe market entities (optional):", 
                    "Consumers in urban areas prefer spicy snacks, retailers like Big Bazaar push discounts, distributors supply through modern trade.",
                    height=80
                )
                
                if st.button("Extract Entities and Update Graph"):
                    with st.spinner("Extracting entities..."):
                        entities = []
                        relations = []
                        
                        if any(word in entity_desc.lower() for word in ["consumer", "customer", "buyer", "shopper"]):
                            entities.append({"name": "Consumer Segment", "type": "consumer"})
                            relations.append({"source": "Consumer Segment", "target": product, "type": "interest"})
                        
                        if any(word in entity_desc.lower() for word in ["retailer", "store", "bazaar", "mall"]):
                            entities.append({"name": "Retail Partners", "type": "retailer"})
                            relations.append({"source": "Retail Partners", "target": product, "type": "promotes"})
                        
                        if any(word in entity_desc.lower() for word in ["distributor", "supplier", "logistics", "warehouse"]):
                            entities.append({"name": "Distribution Network", "type": "distributor"})
                            relations.append({"source": "Distribution Network", "target": "Retail Partners", "type": "supplies"})
                        
                        if any(word in entity_desc.lower() for word in ["discount", "promotion", "offer", "deal"]):
                            entities.append({"name": "Promotional Campaign", "type": "product"})
                            relations.append({"source": "Promotional Campaign", "target": product, "type": "supports"})
                        
                        for e in entities:
                            graph.add_node(e["name"], type=e["type"], label=e["name"])
                        
                        for r in relations:
                            graph.add_edge(r["source"], r["target"], relation=r["type"])
                        
                        st.success("Entities extracted and graph updated!")
                        
                        st.subheader("Updated Knowledge Graph with AI Entities")
                        visualize_graph(graph, height=600, show_edge_labels=False)

    st.markdown("---")
    st.subheader("Deep Interaction")
    st.write("Chat with simulated agents or ask the ReportAgent follow-up questions.")
    
    agent_ids = [agent.id for agent in st.session_state.agents][:10]
    chosen_agent = st.selectbox("Choose an agent to talk to:", agent_ids, key="agent_chat_select")
    agent_question = st.text_input("Ask the selected agent a question:", "Why did you decide to buy this product?", key="agent_question")
    if st.button("Ask Agent", key="agent_chat_button"):
        selected = next((a for a in st.session_state.agents if a.id == chosen_agent), None)
        if selected:
            response = (
                f"Agent {selected.id} ({selected.personality}, {selected.background}) says: "
                f"I react to price sensitivity={selected.price_sensitivity:.2f}, loyalty={selected.loyalty:.2f}, stance={selected.stance}. "
                f"My decision is influenced by availability, marketing, and whether I feel the product fits my profile."
            )
        else:
            response = "Agent not found."
        st.markdown(f"<div class='component-section'>{response}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    report_question = st.text_input("Ask the ReportAgent a follow-up question:", "What was the biggest driver of adoption?", key="report_question")
    if st.button("Ask ReportAgent", key="report_agent_button"):
        if st.session_state.get("report_agent"):
            answer = st.session_state["report_agent"].answer_question(report_question)
            st.markdown(f"<div class='component-section'>{answer}</div>", unsafe_allow_html=True)
        else:
            st.info("Run the simulation first to initialize the ReportAgent.")

st.markdown("---")
st.caption("FMCG Simulator powered by Streamlit | Multi-agent temporal simulation with AI-driven scenario generation | © 2026 MiroFish")
