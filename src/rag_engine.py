"""
rag_engine.py — 340B Dual Discount RAG Engine
==============================================
Retrieval-Augmented Generation system for querying 340B/Medicaid
dual discount risk data using natural language.

Architecture:
  1. Builds text "profiles" from processed 340B + Medicaid data
  2. Embeds profiles with TF-IDF (swap to sentence-transformers for production)
  3. Indexes with FAISS for fast similarity search
  4. Formats retrieved context into LLM prompts
  5. Queries LLM API for natural language answers
"""

import json
import os
import pickle
import numpy as np
import faiss
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


class DualDiscountRAG:
    """RAG engine for 340B dual discount analysis."""

    def __init__(self, index_dir="rag_index"):
        self.index_dir = index_dir
        self.documents = []
        self.metadata = []
        self.vectorizer = None
        self.index = None

    # -----------------------------------------------------------------
    # Index Building
    # -----------------------------------------------------------------

    def build_from_processed_data(self, processed_dir):
        """
        Build RAG documents from the processed data pipeline outputs.
        Creates three types of documents:
          - State risk profiles (one per state)
          - Drug exposure profiles (top 50 drugs)
          - Carve-in arrangement details (grouped by entity)
        """
        print("Building RAG documents from processed data...")
        self.documents = []
        self.metadata = []

        # 1. State risk profiles
        state_df = pd.read_csv(os.path.join(processed_dir, "state_risk_profile.csv"))
        for _, row in state_df.iterrows():
            state = row['State']
            if pd.isna(row['medicaid_spend']) or state == 'XX':
                continue

            text = f"State: {state}\n"
            text += f"Medicaid drug spending (2023): ${row['medicaid_spend']/1e6:,.1f} million\n"
            text += f"Total prescriptions: {row['total_rxs']:,.0f}\n"
            text += f"Unique drugs (NDCs): {row['unique_ndcs']:,.0f}\n"
            text += f"Total 340B covered entities: {int(row['total_entities']):,}\n"
            text += f"DSH hospitals: {int(row['dsh_count']):,}\n"
            text += f"Community health centers: {int(row['ch_count']):,}\n"

            if row['carve_in_arrangements'] > 0:
                text += f"\n--- DUAL DISCOUNT RISK: ACTIVE CARVE-IN ---\n"
                text += f"Carve-in contract pharmacy arrangements: {int(row['carve_in_arrangements']):,}\n"
                text += f"Entities with carve-in: {int(row['carve_in_entities']):,}\n"
                text += f"Unique carve-in pharmacies: {int(row['carve_in_pharmacies']):,}\n"
                text += f"Carve-in rate: {row['carve_in_rate']:.2f}% of all CP arrangements\n"
                text += f"This state has active dual discount risk because 340B contract pharmacies "
                text += f"are billing Medicaid (carve-in), meaning both 340B discounts and Medicaid "
                text += f"rebates may apply to the same drugs.\n"
            else:
                text += f"\nNo carve-in contract pharmacy arrangements detected.\n"
                text += f"Total contract pharmacy arrangements: {int(row['total_cp_arrangements']):,}\n"
                if row['medicaid_spend'] > 1e9:
                    text += f"NOTE: This is a high-spend state (>${row['medicaid_spend']/1e9:.1f}B) "
                    text += f"with {int(row['total_entities']):,} 340B entities but no carve-in data — "
                    text += f"potential oversight gap.\n"

            self.documents.append(text)
            self.metadata.append({
                "type": "state_profile",
                "state": state,
                "has_carve_in": bool(row['carve_in_arrangements'] > 0),
                "medicaid_spend_M": round(row['medicaid_spend'] / 1e6, 1),
            })

        print(f"  {len(self.documents)} state profiles")

        # 2. Drug exposure profiles
        drug_df = pd.read_csv(os.path.join(processed_dir, "top_drugs_carve_in_states.csv"))
        for _, row in drug_df.head(50).iterrows():
            name = str(row['Product Name']).strip()
            text = f"Drug: {name}\n"
            text += f"Medicaid spending in carve-in states: ${row['medicaid_spend']/1e6:,.1f} million\n"
            text += f"Total prescriptions: {row['total_rxs']:,.0f}\n"
            text += f"Present in {int(row['states'])} carve-in states\n"
            text += f"This drug represents significant dual discount exposure because it has "
            text += f"high Medicaid volume flowing through states with active 340B carve-in "
            text += f"contract pharmacy arrangements.\n"

            self.documents.append(text)
            self.metadata.append({
                "type": "drug_exposure",
                "drug_name": name,
                "medicaid_spend_M": round(row['medicaid_spend'] / 1e6, 1),
            })

        print(f"  {len(self.documents)} total documents (with drugs)")

        # 3. Carve-in arrangement details (grouped by entity)
        carve_path = os.path.join(processed_dir, "carve_in_arrangements.csv")
        if os.path.exists(carve_path):
            carve_df = pd.read_csv(carve_path, low_memory=False)
            for (ce_id, name), group in carve_df.groupby(['CE ID', 'Entity Name']):
                state = group['State'].iloc[0]
                entity_type = group['Entity Type'].iloc[0]
                text = f"340B Entity: {name}\n"
                text += f"Entity Type: {entity_type}\n"
                text += f"CE ID: {ce_id}\n"
                text += f"State: {state}\n"
                text += f"Number of carve-in contract pharmacies: {len(group)}\n"
                text += f"Pharmacies:\n"
                for _, r in group.iterrows():
                    text += f"  - {r['Pharmacy Name']} ({r['City']}, {r['State']})\n"
                    if pd.notna(r.get('Carve-In Effective Date')):
                        text += f"    Carve-in effective: {r['Carve-In Effective Date']}\n"
                text += f"\nThis entity has active Medicaid billing through its 340B contract "
                text += f"pharmacies, creating dual discount risk.\n"

                self.documents.append(text)
                self.metadata.append({
                    "type": "entity_carve_in",
                    "entity_name": str(name),
                    "state": str(state),
                    "entity_type": str(entity_type),
                    "num_pharmacies": len(group),
                })

            print(f"  {len(self.documents)} total documents (with entities)")

        # 4. Summary document
        summary_path = os.path.join(processed_dir, "pipeline_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path) as f:
                summary = json.load(f)
            text = "=== 340B DUAL DISCOUNT NATIONAL SUMMARY ===\n"
            text += f"Total active 340B covered entities: {summary['total_active_entities']:,}\n"
            text += f"Total contract pharmacy arrangements: {summary['total_cp_arrangements']:,}\n"
            text += f"Carve-in arrangements (Medicaid Billing = Yes): {summary['carve_in_arrangements']:,}\n"
            text += f"Carve-in rate: {summary['carve_in_rate_pct']}%\n"
            text += f"States with carve-in activity: {', '.join(summary['carve_in_states'])}\n"
            text += f"Total Medicaid drug spending (2023): ${summary['total_medicaid_spend_B']}B\n"
            text += f"Medicaid spending in carve-in states: ${summary['carve_in_states_medicaid_spend_B']}B\n"
            text += f"\nThe dual discount problem occurs when drug manufacturers are subject to both "
            text += f"340B discounted pricing and Medicaid drug rebates on the same prescription. "
            text += f"Federal law prohibits this, but enforcement is challenging because state "
            text += f"Medicaid programs must identify which claims involve 340B drugs. Only {summary['carve_in_rate_pct']}% "
            text += f"of contract pharmacy arrangements are flagged as carve-in (billing Medicaid), "
            text += f"concentrated in {len(summary['carve_in_states'])} states.\n"

            self.documents.append(text)
            self.metadata.append({"type": "summary"})

        self._build_vectors()

    def _build_vectors(self):
        """Build TF-IDF vectors and FAISS index."""
        print("Building TF-IDF vectors...")
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2),
            sublinear_tf=True,
            dtype=np.float32,
        )
        tfidf = self.vectorizer.fit_transform(self.documents)
        dense = tfidf.toarray()
        faiss.normalize_L2(dense)

        d = dense.shape[1]
        self.index = faiss.IndexFlatIP(d)
        self.index.add(dense)
        print(f"  FAISS index: {self.index.ntotal} documents x {d} dims")

        # Save
        os.makedirs(self.index_dir, exist_ok=True)
        faiss.write_index(self.index, os.path.join(self.index_dir, "340b.faiss"))
        with open(os.path.join(self.index_dir, "vectorizer.pkl"), "wb") as f:
            pickle.dump(self.vectorizer, f)
        with open(os.path.join(self.index_dir, "documents.json"), "w") as f:
            json.dump(self.documents, f)
        with open(os.path.join(self.index_dir, "metadata.json"), "w") as f:
            json.dump(self.metadata, f)
        print("  Index saved!")

    def load_index(self):
        """Load pre-built index from disk."""
        self.index = faiss.read_index(os.path.join(self.index_dir, "340b.faiss"))
        with open(os.path.join(self.index_dir, "vectorizer.pkl"), "rb") as f:
            self.vectorizer = pickle.load(f)
        with open(os.path.join(self.index_dir, "documents.json")) as f:
            self.documents = json.load(f)
        with open(os.path.join(self.index_dir, "metadata.json")) as f:
            self.metadata = json.load(f)
        print(f"  Index loaded: {self.index.ntotal} documents")

    # -----------------------------------------------------------------
    # Search & Retrieval
    # -----------------------------------------------------------------

    def search(self, query, k=5, doc_type=None, state_filter=None):
        """
        Search for documents matching a natural language query.

        Args:
            query: Natural language question
            k: Number of results
            doc_type: Filter by type (state_profile, drug_exposure, entity_carve_in, summary)
            state_filter: Filter by state abbreviation
        """
        q_vec = self.vectorizer.transform([query]).toarray().astype(np.float32)
        faiss.normalize_L2(q_vec)

        search_k = k * 10 if (doc_type or state_filter) else k
        distances, indices = self.index.search(q_vec, min(search_k, len(self.documents)))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            if doc_type and meta.get("type") != doc_type:
                continue
            if state_filter and meta.get("state", "").upper() != state_filter.upper():
                continue
            results.append({
                "score": float(dist),
                "metadata": meta,
                "text": self.documents[idx],
            })
            if len(results) >= k:
                break
        return results

    # -----------------------------------------------------------------
    # LLM Integration
    # -----------------------------------------------------------------

    def build_prompt(self, query, results):
        """Format retrieved documents into an LLM prompt."""
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[Document {i} | Type: {r['metadata'].get('type','')} | "
                                 f"Score: {r['score']:.3f}]")
            context_parts.append(r['text'])
            context_parts.append("")

        context = "\n".join(context_parts)

        return f"""You are an expert healthcare policy analyst specializing in the 340B Drug Pricing Program
and its intersection with Medicaid. You have access to data from HRSA's 340B OPAIS system and
CMS State Drug Utilization Data for 2023.

Answer the user's question using ONLY the data provided below. Be specific — cite numbers,
percentages, dollar amounts, and state names from the data. If the data doesn't fully answer
the question, say so and explain what additional data would be needed.

RETRIEVED DATA:
{context}

USER QUESTION: {query}

Provide a thorough, data-driven answer:"""

    def query_with_llm(self, query, k=8, api_key=None, model=None, provider="openrouter"):
        """
        Full RAG pipeline: retrieve relevant documents, then generate answer with LLM.

        Args:
            query: Natural language question
            k: Number of documents to retrieve
            api_key: API key (or set OPENROUTER_API_KEY / OPENAI_API_KEY env var)
            model: Model name (default: anthropic/claude-sonnet-4 for OpenRouter)
            provider: 'openrouter' or 'openai'
        """
        import requests

        results = self.search(query, k=k)
        if not results:
            return "No relevant data found for your query."

        prompt = self.build_prompt(query, results)

        api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("[No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY]")
            print("\nRetrieved context:")
            for r in results:
                print(f"\n--- {r['metadata'].get('type','')} (score: {r['score']:.3f}) ---")
                print(r['text'][:500])
            return None

        if provider == "openrouter" or os.environ.get("OPENROUTER_API_KEY"):
            url = "https://openrouter.ai/api/v1/chat/completions"
            model = model or "anthropic/claude-sonnet-4"
        else:
            url = "https://api.openai.com/v1/chat/completions"
            model = model or "gpt-4o-mini"

        resp = requests.post(url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000})
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="340B RAG Engine")
    parser.add_argument("--build", action="store_true", help="Build index from processed data")
    parser.add_argument("--data-dir", default="data/processed", help="Processed data directory")
    parser.add_argument("--index-dir", default="rag_index", help="Index directory")
    parser.add_argument("--query", type=str, help="Query the index")
    parser.add_argument("--state", type=str, help="Filter by state")
    parser.add_argument("--llm", action="store_true", help="Use LLM for answer generation")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    rag = DualDiscountRAG(index_dir=args.index_dir)

    if args.build:
        rag.build_from_processed_data(args.data_dir)
    else:
        rag.load_index()

    if args.interactive:
        print("\n340B Dual Discount RAG — Interactive Mode")
        print("Type 'quit' to exit.\n")
        while True:
            q = input("Query> ").strip()
            if q.lower() in ('quit', 'exit', 'q'):
                break
            if args.llm:
                answer = rag.query_with_llm(q)
                if answer:
                    print(f"\n{answer}\n")
            else:
                results = rag.search(q, k=5, state_filter=args.state)
                for r in results:
                    print(f"\n--- {r['metadata'].get('type','')} (score: {r['score']:.3f}) ---")
                    print(r['text'])

    elif args.query:
        if args.llm:
            answer = rag.query_with_llm(args.query)
            if answer:
                print(answer)
        else:
            results = rag.search(args.query, k=5, state_filter=args.state)
            for r in results:
                print(f"\n--- {r['metadata'].get('type','')} (score: {r['score']:.3f}) ---")
                print(r['text'])
