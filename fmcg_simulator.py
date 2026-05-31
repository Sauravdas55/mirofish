# --- FMCG Simulator with Knowledge Graph + Agents + Reports ---
# Save as fmcg_simulator.py
# Run with: python -m streamlit run fmcg_simulator.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx   # For knowledge graph

from pyvis.network import Network
import streamlit.components.v1 as components
import time   # <-- make sure this line is present

def visualize_graph(G):
    # Create a PyVis network object
    net = Network(height="500px", width="100%", bgcolor="#222222", font_color="white")

    # Add nodes with colors based on type
    for node, data in G.nodes(data=True):
        if data.get("type") == "product":
            net.add_node(node, label=node, color="red", shape="ellipse")
        elif data.get("type") == "consumer":
            net.add_node(node, label=node, color="green", shape="dot")
        else:
            net.add_node(node, label=node, color="blue")

    # Add edges with labels
    for source, target, data in G.edges(data=True):
        relation = data.get("relation", "")
        net.add_edge(source, target, label=relation, color="orange")

    # Save visualization to HTML
    net.write_html("graph.html")

    # Load HTML file and display inside Streamlit
    with open("graph.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=550)

# Initialize an empty graph with the product node
G = nx.Graph()
G.add_node("Spicy Snack", type="product")

# --- Dynamic Graph Visualization Example ---

with st.expander("🔄 Real-Time Graph Relationship Visualization (demo)"):
    placeholder = st.empty()
    for step in range(5):
        new_consumer = f"Consumer_{step}"
        G.add_node(new_consumer, type="consumer")
        G.add_edge(new_consumer, "Spicy Snack", relation="buys")
        with placeholder:
            visualize_graph(G)
        time.sleep(2)

# -----------------------------
# Step 1: Define Consumer Agent
# -----------------------------
class ConsumerAgent:
    def __init__(self, id, age_group, income_level, price_sensitivity, loyalty):
        self.id = id
        self.age_group = age_group
        self.income_level = income_level
        self.price_sensitivity = price_sensitivity
        self.loyalty = loyalty

    def decide_purchase(self, product_price, marketing_push):
        # Simple probability model
        price_factor = 1 - (self.price_sensitivity * (product_price / 25))
        loyalty_factor = 1 - self.loyalty * 0.5
        marketing_factor = marketing_push
        prob = max(0, min(1, price_factor * (1 - loyalty_factor) + marketing_factor))
        return np.random.rand() < prob, prob

# -----------------------------
# Step 2: Build Knowledge Graph
# -----------------------------
def build_graph(consumers, product_name):
    G = nx.Graph()
    G.add_node(product_name, type="product")
    for c in consumers:
        G.add_node(c.id, type="consumer", age=c.age_group, income=c.income_level)
        G.add_edge(c.id, product_name, relation="potential_buyer")
    return G

# -----------------------------
# Step 3: Run Simulation
# -----------------------------
def run_simulation(base_price, marketing_push):
    # Generate synthetic agents
    agents = [
        ConsumerAgent(
            id=i,
            age_group=np.random.choice(["18-25", "26-40", "41-60"]),
            income_level=np.random.choice(["low", "mid", "high"]),
            price_sensitivity=np.random.rand(),
            loyalty=np.random.rand()
        )
        for i in range(1, 101)
    ]

    # Simulate purchases
    results = []
    for agent in agents:
        adopted, prob = agent.decide_purchase(base_price, marketing_push)
        results.append({
            "consumer_id": agent.id,
            "age_group": agent.age_group,
            "income_level": agent.income_level,
            "price_sensitivity": agent.price_sensitivity,
            "loyalty": agent.loyalty,
            "adoption_prob": prob,
            "adopted": adopted
        })

    df = pd.DataFrame(results)
    adoption_rate = df["adopted"].mean()

    # Build knowledge graph
    G = build_graph(agents, "Spicy Snack")

    return df, adoption_rate, G

# -----------------------------
# Step 4: Streamlit Dashboard
# -----------------------------
# -----------------------------
# Step 4: Streamlit Dashboard
# -----------------------------
st.title("🍿 FMCG Product Launch Simulator (MiroFish Prototype)")

# User inputs
base_price = st.slider("Set Product Price (₹)", min_value=10, max_value=50, value=20, step=1)
marketing_push = st.slider("Marketing Push Strength", min_value=0.0, max_value=1.0, value=0.7, step=0.1)

# --- Run simulation ---
# --- Run simulation ---
df, adoption_rate, G = run_simulation(base_price, marketing_push)

# --- Ontology Extraction (optional enrichment) ---
from langchain_community.llms import Ollama
llm = Ollama(model="llama3")

ontology_prompt = """
Extract entities and relationships from this FMCG text:
'Consumers in Pune prefer spicy snacks, retailers push discounts, distributors supply bulk orders.'
Return JSON with entities and relations.
"""

response = llm.invoke(ontology_prompt)

# Example stub until you parse actual JSON
entities = [{"name":"Consumer_Pune","type":"consumer"},
            {"name":"Retailer","type":"retailer"},
            {"name":"Distributor","type":"distributor"}]
relations = [{"source":"Consumer_Pune","target":"Spicy Snack","type":"buys"},
             {"source":"Retailer","target":"Spicy Snack","type":"promotes"},
             {"source":"Distributor","target":"Retailer","type":"supplies"}]

for e in entities:
    G.add_node(e["name"], type=e["type"])
for r in relations:
    G.add_edge(r["source"], r["target"], relation=r["type"])

# --- Continue with dashboard sections ---
st.metric(label="Predicted Adoption Rate", value=f"{adoption_rate:.2%}")

# Histogram
fig, ax = plt.subplots()
ax.hist(df["adoption_prob"], bins=10, color="orange", edgecolor="black")
ax.set_title("Distribution of Adoption Probabilities")
ax.set_xlabel("Adoption Probability")
ax.set_ylabel("Number of Consumers")
st.pyplot(fig)

# Reports
st.subheader("📑 Adoption Report by Age Group")
st.write(df.groupby("age_group")["adopted"].mean())

st.subheader("📑 Adoption Report by Income Level")
st.write(df.groupby("income_level")["adopted"].mean())

# Graph visualization
st.subheader("📊 Final Graph Snapshot")
visualize_graph(G)

# Sample consumer data
st.subheader("Sample Consumer Data")
st.dataframe(df.head(10))

# Knowledge Graph summary
st.subheader("Knowledge Graph Summary")
st.write(f"Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")