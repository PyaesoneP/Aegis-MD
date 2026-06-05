from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

folder_path = Path("data/guidelines")

loaders = []

for file in folder_path.iterdir():
    if file.is_file() and file.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(file))
        loaders.append(loader)

docs = []

for loader in loaders:
    docs.extend(loader.load())

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)

splits = text_splitter.split_documents(docs)

client = chromadb.PersistentClient(path="data/chroma/chroma_db")
collection = client.get_or_create_collection(name="guidelines")


collection.add(
    documents=[split.page_content for split in splits],
    ids=[f"{split.metadata['source']} : {split.metadata['page']} : chunk_index_{i}" for i, split in enumerate(splits)],
    metadatas=[{
        "source": split.metadata["source"],
        "page_number": split.metadata["page"]
    } for split in splits]
)
    