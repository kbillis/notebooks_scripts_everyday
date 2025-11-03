import streamlit as st
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain_community.utilities import GoogleSerperAPIWrapper
import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

# Check for GPU
device = 0 if torch.cuda.is_available() else -1
device_name = "GPU" if device == 0 else "CPU"

st.set_page_config(page_title="Last Week In...", page_icon="📰", layout="wide")

# ═══════════════════════════════════════════════════════════════════
# MODEL SELECTION & CACHING
# ═══════════════════════════════════════════════════════════════════

@st.cache_resource
def load_summarization_model(model_name):
    """Load and cache the summarization model."""
    try:
        if model_name == "facebook/bart-large-cnn":
            # BART - Great for news summarization (400MB)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            summarizer = pipeline(
                "summarization",
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_length=150,
                min_length=50,
                do_sample=False
            )
        elif model_name == "google/pegasus-xsum":
            # Pegasus - Excellent for abstractive summarization (568MB)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            summarizer = pipeline(
                "summarization",
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_length=150,
                min_length=50
            )
        elif model_name == "sshleifer/distilbart-cnn-12-6":
            # DistilBART - Faster, smaller (306MB)
            summarizer = pipeline(
                "summarization",
                model=model_name,
                device=device,
                max_length=150,
                min_length=50
            )
        elif model_name == "facebook/mbart-large-50":
            # mBART - Multilingual support (2.4GB)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            summarizer = pipeline(
                "summarization",
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_length=150,
                min_length=50
            )
        elif model_name == "philschmid/flan-t5-base-samsum":
            # FLAN-T5 - Instruction-tuned (250MB)
            summarizer = pipeline(
                "summarization",
                model=model_name,
                device=device,
                max_length=150,
                min_length=50
            )
        else:
            # Default to DistilBART
            summarizer = pipeline(
                "summarization",
                model="sshleifer/distilbart-cnn-12-6",
                device=device,
                max_length=150,
                min_length=50
            )
        return summarizer
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

def chunk_text(text, max_length=1024):
    """Split text into chunks that fit model's context window."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        if current_length > max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def summarize_text(text, summarizer, model_name):
    """Summarize text, handling long documents."""
    try:
        # Clean text
        text = text.strip()
        if len(text) < 100:
            return "Text too short to summarize."
        
        # Chunk if necessary
        chunks = chunk_text(text, max_length=1024)
        
        summaries = []
        for chunk in chunks[:3]:  # Limit to first 3 chunks to avoid timeout
            try:
                if model_name == "philschmid/flan-t5-base-samsum":
                    # FLAN-T5 works better with instruction
                    result = summarizer(f"Summarize this article: {chunk}", max_length=150, min_length=50)
                else:
                    result = summarizer(chunk, max_length=150, min_length=50)
                
                if result and len(result) > 0:
                    summaries.append(result[0]['summary_text'])
            except Exception as e:
                st.warning(f"Chunk summarization failed: {e}")
                continue
        
        if summaries:
            # If multiple chunks, combine summaries
            if len(summaries) > 1:
                combined = " ".join(summaries)
                # Summarize again if too long
                if len(combined.split()) > 200:
                    final = summarizer(combined, max_length=150, min_length=50)
                    return final[0]['summary_text']
                return combined
            return summaries[0]
        else:
            return "Could not generate summary."
    except Exception as e:
        return f"Summarization error: {str(e)}"

def scrape_article_content(url):
    """Scrape article content from URL using BeautifulSoup."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Try to find article content
        article = None
        for tag in ['article', 'main', 'div[class*="content"]', 'div[class*="article"]']:
            article = soup.find(tag)
            if article:
                break
        
        if not article:
            article = soup.find('body')
        
        # Get text
        text = article.get_text(separator=' ', strip=True) if article else ""
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text[:5000]  # Limit to first 5000 chars
    except Exception as e:
        st.warning(f"Scraping failed: {e}")
        return ""

# ═══════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ═══════════════════════════════════════════════════════════════════

st.title('📰 Last Week In...')
st.caption(f'🖥️ Running on: **{device_name}** | 🤖 Powered by Open Source Transformers')

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Model selection
    st.subheader("🤖 Summarization Model")
    model_options = {
        "BART-Large (Best Quality)": "facebook/bart-large-cnn",
        "Pegasus-XSum (Abstractive)": "google/pegasus-xsum",
        "DistilBART (Fastest)": "sshleifer/distilbart-cnn-12-6",
        "FLAN-T5 (Instruction-tuned)": "philschmid/flan-t5-base-samsum",
        "mBART (Multilingual)": "facebook/mbart-large-50"
    }
    
    selected_model_name = st.selectbox(
        "Choose model",
        options=list(model_options.keys()),
        index=2,  # Default to DistilBART (fastest)
        help="BART/Pegasus: Best quality but slower. DistilBART: Good balance. FLAN-T5: Fast & efficient."
    )
    selected_model = model_options[selected_model_name]
    
    st.info(f"**Model:** {selected_model_name}\n\n"
            f"**Device:** {device_name}\n\n"
            f"⚡ First run will download model (~300-600MB)")
    
    st.divider()
    
    # Search configuration
    st.subheader("🔍 Search Settings")
    serper_api_key = st.text_input(
        "Serper API Key",
        value="",
        type="password",
        help="Get free API key from serper.dev"
    )
    
    num_results = st.slider(
        "Number of Results",
        min_value=3,
        max_value=10,
        value=5,
        help="Number of articles to fetch"
    )
    
    use_langchain = st.checkbox(
        "Use LangChain Loader",
        value=False,
        help="Uses UnstructuredURLLoader (slower but more reliable)"
    )
    
    st.divider()
    
    st.caption("**Search:** Retrieves news articles")
    st.caption("**Search & Summarize:** Retrieves + AI summarization")
    st.caption("**💡 Tip:** Use GPU for 5-10x faster summarization")

# Main search input
search_query = st.text_input(
    "🔎 What are you interested in?",
    placeholder="e.g., artificial intelligence, cryptocurrency, climate change...",
    label_visibility="visible"
)

col1, col2, col3 = st.columns([1, 1, 2])

# ═══════════════════════════════════════════════════════════════════
# SEARCH BUTTON
# ═══════════════════════════════════════════════════════════════════

if col1.button("🔍 Search", use_container_width=True):
    if not serper_api_key.strip() or not search_query.strip():
        st.error("⚠️ Please provide Serper API key and search query.")
    else:
        try:
            with st.spinner("🔎 Searching news..."):
                # Search using Google Serper API
                search = GoogleSerperAPIWrapper(
                    type="news",
                    tbs="qdr:w1",
                    serper_api_key=serper_api_key
                )
                result_dict = search.results(search_query)

                if not result_dict.get('news'):
                    st.error(f"❌ No search results for: **{search_query}**")
                else:
                    st.success(f"✅ Found {len(result_dict['news'])} articles")
                    
                    for i, item in enumerate(result_dict['news'][:num_results], 1):
                        with st.expander(f"📄 {i}. {item['title']}", expanded=(i==1)):
                            st.markdown(f"**🔗 Link:** [{item['link']}]({item['link']})")
                            st.markdown(f"**📝 Snippet:** {item['snippet']}")
                            if 'date' in item:
                                st.caption(f"📅 {item['date']}")
        except Exception as e:
            st.exception(f"❌ Exception: {e}")

# ═══════════════════════════════════════════════════════════════════
# SEARCH & SUMMARIZE BUTTON
# ═══════════════════════════════════════════════════════════════════

if col2.button("✨ Search & Summarize", use_container_width=True):
    if not serper_api_key.strip() or not search_query.strip():
        st.error("⚠️ Please provide Serper API key and search query.")
    else:
        try:
            # Load model
            with st.spinner(f"🤖 Loading {selected_model_name}..."):
                summarizer = load_summarization_model(selected_model)
                
            if summarizer is None:
                st.error("❌ Failed to load summarization model.")
            else:
                with st.spinner("🔎 Searching news..."):
                    search = GoogleSerperAPIWrapper(
                        type="news",
                        tbs="qdr:w1",
                        serper_api_key=serper_api_key
                    )
                    result_dict = search.results(search_query)

                    if not result_dict.get('news'):
                        st.error(f"❌ No search results for: **{search_query}**")
                    else:
                        st.success(f"✅ Found {len(result_dict['news'])} articles. Summarizing...")
                        
                        progress_bar = st.progress(0)
                        
                        for i, item in enumerate(result_dict['news'][:num_results], 1):
                            progress_bar.progress(i / num_results)
                            
                            with st.expander(f"📄 {i}. {item['title']}", expanded=(i==1)):
                                st.markdown(f"**🔗 Link:** [{item['link']}]({item['link']})")
                                
                                # Load content
                                with st.spinner(f"Loading article {i}/{num_results}..."):
                                    if use_langchain:
                                        try:
                                            loader = UnstructuredURLLoader(
                                                urls=[item['link']],
                                                ssl_verify=False,
                                                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"}
                                            )
                                            data = loader.load()
                                            article_text = data[0].page_content if data else ""
                                        except:
                                            article_text = scrape_article_content(item['link'])
                                    else:
                                        article_text = scrape_article_content(item['link'])
                                
                                if not article_text or len(article_text) < 100:
                                    st.warning("⚠️ Could not extract article content. Using snippet instead.")
                                    article_text = item['snippet']
                                
                                # Summarize
                                with st.spinner("✨ Generating summary..."):
                                    summary = summarize_text(article_text, summarizer, selected_model)
                                
                                # Display
                                st.markdown("**🤖 AI Summary:**")
                                st.info(summary)
                                
                                with st.expander("📋 Original snippet"):
                                    st.write(item['snippet'])
                                
                                if 'date' in item:
                                    st.caption(f"📅 {item['date']}")
                        
                        progress_bar.progress(1.0)
                        st.balloons()
                        
        except Exception as e:
            st.exception(f"❌ Exception: {e}")

# ═══════════════════════════════════════════════════════════════════
# BATCH SUMMARIZE (BONUS FEATURE)
# ═══════════════════════════════════════════════════════════════════

if col3.button("📊 Search & Compare All Models", use_container_width=True):
    if not serper_api_key.strip() or not search_query.strip():
        st.error("⚠️ Please provide Serper API key and search query.")
    else:
        try:
            with st.spinner("🔎 Searching news..."):
                search = GoogleSerperAPIWrapper(
                    type="news",
                    tbs="qdr:w1",
                    serper_api_key=serper_api_key
                )
                result_dict = search.results(search_query)

                if not result_dict.get('news'):
                    st.error(f"❌ No search results for: **{search_query}**")
                else:
                    # Get first article
                    item = result_dict['news'][0]
                    st.subheader(f"📄 {item['title']}")
                    st.markdown(f"**🔗 Link:** [{item['link']}]({item['link']})")
                    
                    # Load content
                    article_text = scrape_article_content(item['link'])
                    
                    if not article_text or len(article_text) < 100:
                        st.warning("Using snippet for comparison")
                        article_text = item['snippet']
                    
                    st.divider()
                    st.subheader("🤖 Model Comparison")
                    
                    # Test all models
                    models_to_test = [
                        ("DistilBART (Fast)", "sshleifer/distilbart-cnn-12-6"),
                        ("BART-Large (Quality)", "facebook/bart-large-cnn"),
                        ("FLAN-T5 (Efficient)", "philschmid/flan-t5-base-samsum")
                    ]
                    
                    for model_display, model_path in models_to_test:
                        with st.spinner(f"Testing {model_display}..."):
                            test_summarizer = load_summarization_model(model_path)
                            if test_summarizer:
                                summary = summarize_text(article_text, test_summarizer, model_path)
                                
                                with st.expander(f"✨ {model_display}", expanded=True):
                                    st.info(summary)
                    
                    st.success("✅ Comparison complete! Choose your favorite model in the sidebar.")
                    
        except Exception as e:
            st.exception(f"❌ Exception: {e}")

# Footer
st.divider()
st.caption("🤖 **Powered by:** Hugging Face Transformers | 🔍 **Search:** Serper API | 💡 **100% Open Source**")
st.caption("📦 **Models:** BART, Pegasus, DistilBART, FLAN-T5, mBART | 🚀 **GPU Accelerated**")
