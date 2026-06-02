นี่คือไฟล์มาร์กดาวน์ (**Implementation Plan**) ฉบับสมบูรณ์ที่ออกแบบมาตามความต้องการของคุณทั้งหมด โดยใช้ **LlamaIndex + Typhoon + ChromaDB** ร่วมกับระบบ Dynamic Folder Mapping ด้วย **JSON** และการตั้งค่า **Shortcut Command (`rag`)** ผ่าน Python Virtual Environment ครับ

คุณสามารถบันทึกเนื้อหาด้านล่างนี้เป็นไฟล์ชื่อ `implementation_plan.md` เพื่อนำไปใช้งานได้ทันทีครับ:

---

```markdown
# 🚀 Implementation Plan: Antigravity Agentic RAG CLI
ระบบ Agentic RAG บนระบบโครงสร้างโฟลเดอร์แบบยืดหยุ่น ขับเคลื่อนด้วย LlamaIndex, Typhoon LLM, และ ChromaDB พร้อมระบบ Shortcut Command (`rag`)

---

## 🏗️ System Architecture & Data Flow


```

[ User: พิมพ์คำสั่ง 'rag' ]
│
▼
( เปิดหน้าต่าง CLI Prompt )
│
▼
[ ป้อนคำถามผู้ใช้ ]
│
▼
[ Supervisor Router Agent ] ◄── โหลดโฟลเดอร์และคำอธิบายแบบ Dynamic จาก `config.json`
│
┌─────────┴─────────┐
▼ (เลือกคลังที่ใช่)      ▼ (เลือกคลังที่ใช่)
[ คลังข้อมูล Finance ]    [ คลังข้อมูล HR ]  ... (สเกลเพิ่มได้ไม่จำกัด)
│                   │
└─────────┬─────────┘
▼
[ ค้นหา Vector + ดึง Text ดิบ ] ◄── ดึงเฉพาะ Collection ใน ChromaDB ที่เจาะจง
│
▼
[ Typhoon LLM Generator ]
│
▼
[ พ่นคำตอบภาษาไทยสละสลวยบน CLI ]

```

---

## 🛠️ Phase 1: Environment Setup & Directory Structure

เราจะทำการแยกสภาพแวดล้อมการทำงานด้วย `venv` และโครงสร้างโฟลเดอร์ให้รองรับการขยายตัว (Scale) ของเอกสารในอนาคต

### 1.1 สร้างโปรเจกต์และตั้งค่า Virtual Environment (venv)
เปิด Terminal แล้วรันคำสั่งต่อไปนี้เพื่อเตรียมสภาพแวดล้อม:

```bash
# 1. สร้างโฟลเดอร์โปรเจกต์และย้ายเข้าไป
mkdir antigravity-rag-cli
cd antigravity-rag-cli

# 2. สร้าง Python Virtual Environment ชื่อ .venv
python3 -m venv .venv

# 3. เปิดใช้งาน (Activate) venv
# สำหรับ macOS / Linux:
source .venv/bin/activate
# สำหรับ Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 4. อัปเกรด pip และติดตั้งไลบรารีทั้งหมดที่จำเป็น
pip install --upgrade pip
pip install llamaindex typer chromadb llama-index-vector-stores-chromadb llama-index-llms-openai-like pypdf

```

### 1.2 โครงสร้างไดเรกทอรีของโปรเจกต์ (Project Structure)

สร้างโครงสร้างไฟล์และโฟลเดอร์ให้มีลักษณะดังนี้:

```text
antigravity-rag-cli/
│
├── .venv/                   # Python Virtual Environment
├── storage/                 # โฟลเดอร์เก็บฐานข้อมูล ChromaDB (Local Disk)
│
├── documents/               # โฟลเดอร์เก็บเอกสาร PDF แยกตามหมวดหมู่
│   ├── Finance/
│   │   └── budget_2026.pdf
│   └── HR/
│       └── welfare_manual.pdf
│
├── config.json              # ไฟล์ควบคุมคลังเอกสารและคำอธิบายสำหรับ Agent
├── rag_agent.py             # ส่วนประมวลผลหลัก (LlamaIndex + Typhoon + ChromaDB)
└── main.py                  # จุดรันโปรแกรมอินเทอร์เฟซ CLI (Typer)

```

---

## 🗂️ Phase 2: Configuration & Dynamic Loading (Scale-Ready)

เพื่อความง่ายต่อการเพิ่มคลังเอกสารใหม่ๆ ในอนาคตโดยไม่ต้องกลับมาแก้ไขโค้ด (Easy to Scale) เราจะใช้ไฟล์ `config.json` เป็นตัวระบุความสัมพันธ์และ Metadata

### 2.1 สร้างไฟล์ `config.json`

ไฟล์นี้จะเก็บเส้นทางโฟลเดอร์เอกสาร ชื่อคอลเลกชันในฐานข้อมูล และ**คำอธิบาย (Description)** ที่สำคัญมากในการให้ AI ใช้ตัดสินใจเลือกโฟลเดอร์:

```json
{
  "directories": [
    {
      "name": "Finance",
      "path": "./documents/Finance",
      "collection_name": "finance_collection",
      "description": "ใช้สำหรับค้นหาข้อมูลที่เกี่ยวข้องกับการเงิน งบประมาณ รายจ่ายประจำปี 2026 ตัวเลขทางการบัญชี และข้อมูลภาษีขององค์กร"
    },
    {
      "name": "HR",
      "path": "./documents/HR",
      "collection_name": "hr_collection",
      "description": "ใช้สำหรับค้นหาข้อมูลเกี่ยวกับทรัพยากรบุคคล กฎระเบียบบริษัท คู่มือพนักงาน นโยบายสวัสดิการ การเบิกค่ารักษาพยาบาล และขั้นตอนการลางาน"
    }
  ]
}

```

*💡 **การขยายระบบ (Scaling):** ในอนาคตหากมีโฟลเดอร์เอกสารใหม่ เช่น `./documents/Legal` คุณเพียงแค่นำเอกสาร PDF ไปหย่อนลงโฟลเดอร์นั้น แล้วมาเขียนเพิ่มในไฟล์ `config.json` นี้อีก 1 บล็อก ระบบ RAG จะขยายขีดความสามารถตามทันทีโดยอัตโนมัติ*

---

## 🤖 Phase 3: Core Implementation (LlamaIndex + Typhoon + ChromaDB)

### 3.1 เขียนไฟล์ระบบค้นหาหลัก `rag_agent.py`

ไฟล์นี้ทำหน้าที่โหลด Config, จัดการแปลง PDF ลง ChromaDB และตั้งค่า Typhoon LLM เป็นตัวคิดสืบค้นข้อมูล

```python
import json
import os
import chromadb
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chromadb import ChromaVectorStore

# 1. ตั้งค่า Global LLM ให้เป็น Typhoon (ปรับอุณหภูมิให้ต่ำเพื่อให้ Router ทำงานได้แม่นยำ)
TYPHOON_API_KEY = os.getenv("TYPHOON_API_KEY", "your-typhoon-api-key-here")

Settings.llm = OpenAILike(
    model="typhoon-v1.5x-70b-instruct",
    api_base="[https://api.opentyphoon.ai/v1](https://api.opentyphoon.ai/v1)",
    api_key=TYPHOON_API_KEY,
    temperature=0.1
)

# 2. เปิดการเชื่อมต่อฐานข้อมูล ChromaDB แบบ Local Persistent
CHROMA_DB_PATH = "./storage/chroma_db"
db_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

def load_config():
    """โหลดโครงสร้างและคำอธิบายโฟลเดอร์จากไฟล์ JSON"""
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def sync_all_documents():
    """สแกนทุกโฟลเดอร์ตาม JSON และอัปเดตไฟล์ PDF เข้า Vector DB"""
    config = load_config()
    for dir_info in config["directories"]:
        path = dir_info["path"]
        collection_name = dir_info["collection_name"]
        
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"📁 สร้างโฟลเดอร์เปล่า: {path} (กรุณานำไฟล์ PDF ไปใส่)")
            continue
            
        print(f"🔄 กำลังประมวลผลไฟล์ PDF จากโฟลเดอร์: {path} เข้าสู่คอลเลกชัน {collection_name}...")
        
        # เชื่อมต่อถังเก็บข้อมูลแยกตามคอลเลกชัน
        chroma_collection = db_client.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # อ่าน PDF และสร้างสัจพจน์ตัวเลข (Embedding)
        documents = SimpleDirectoryReader(input_dir=path).load_data()
        VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        
    print("✅ อัปเดตข้อมูลเอกสารทั้งหมดลงฐานข้อมูล ChromaDB เรียบร้อยแล้ว!")

def build_agentic_router_engine():
    """ประกอบร่าง Dynamic Router Agent โดยอ้างอิงจากรายละเอียดใน JSON"""
    config = load_config()
    query_engine_tools = []
    individual_engines = {}
    
    for dir_info in config["directories"]:
        name = dir_info["name"]
        collection_name = dir_info["collection_name"]
        description = dir_info["description"]
        
        # โหลดคลังข้อความของแต่ละโฟลเดอร์ขึ้นมาสร้างเป็น Query Engine
        chroma_collection = db_client.get_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        index = VectorStoreIndex.from_vector_store(vector_store)
        engine = index.as_query_engine()
        
        individual_engines[name.lower()] = engine
        
        # แพ็กใส่เครื่องมือพร้อมคำอธิบายให้ Agent เลือกใช้
        tool = QueryEngineTool.from_defaults(
            query_engine=engine,
            name=f"{name.lower()}_search",
            description=description
        )
        query_engine_tools.append(tool)
        
    # สร้างจุดศูนย์กลางการตัดสินใจเลือกโฟลเดอร์ (Supervisor Agent)
    router_engine = RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(),
        query_engine_tools=query_engine_tools
    )
    
    return router_engine, individual_engines

```

---

## 💻 Phase 4: CLI Application Interface

### 4.1 เขียนโค้ดหน้าบ้าน `main.py`

ใช้ `Typer` ในการสร้างอินเตอร์เฟซบนหน้าจอ Terminal แบบ Interactive Prompt Loop เพื่อให้ผู้ใช้ป้อนคำถามได้ต่อเนื่อง

```python
import typer
import rag_agent

app = typer.Typer(help="Antigravity Agentic RAG CLI Tool")

@app.command()
def sync():
    """คำสั่งสำหรับสั่งสแกนและอัปเดตไฟล์ PDF ใหม่ทั้งหมด"""
    rag_agent.sync_all_documents()

@app.command()
def start():
    """คำสั่งเข้าสู่หน้าต่างการพิมพ์โต้ตอบแบบ Agentic RAG Prompt (คำสั่งหลัก)"""
    typer.secho("🤖 ยินดีต้อนรับสู่ Antigravity Agentic RAG CLI!", fg=typer.colors.CYAN, bold=True)
    typer.echo("กำลังโหลดคลังข้อมูลและเชื่อมต่อสมองกล Typhoon...")
    
    try:
        router_engine, individual_engines = rag_agent.build_agentic_router_engine()
    except Exception as e:
        typer.secho("\n❌ เกิดข้อผิดพลาด: ไม่พบข้อมูลในระบบคลัง กรุณารันคำสั่ง `rag sync` ก่อนใช้งานครั้งแรก", fg=typer.colors.RED)
        raise typer.Exit()
        
    typer.secho("✨ ระบบพร้อมใช้งานแล้ว! (พิมพ์ 'exit' หรือ 'quit' เพื่อออกจากโปรแกรม)\n", fg=typer.colors.GREEN)
    
    while True:
        # รับคำถามจากผู้ใช้
        query = typer.prompt("❓ ถามคำถามของคุณ")
        
        if query.lower() in ["exit", "quit"]:
            typer.secho("👋 ออกจากระบบ RAG บายครับ!", fg=typer.colors.YELLOW)
            break
            
        if not query.strip():
            continue
            
        typer.echo("🤖 Agent กำลังคิดและค้นหาโฟลเดอร์เอกสารที่เกี่ยวข้อง...")
        
        try:
            # รันการค้นหาแบบสืบเสาะหาโฟลเดอร์ผ่าน Router Engine
            response = router_engine.query(query)
            
            # แสดงผลลัพธ์ที่ได้กลับมา
            typer.secho("\n" + "="*50, fg=typer.colors.BLUE)
            typer.secho(f"✨ คำตอบ:\n{response}", fg=typer.colors.MAGENTA, bold=True)
            typer.secho("="*50 + "\n", fg=typer.colors.BLUE)
        except Exception as e:
            typer.secho(f"เกิดข้อผิดพลาดในการประมวลผล: {e}\n", fg=typer.colors.RED)

if __name__ == "__main__":
    app()

```

---

## 🚀 Phase 5: Shortcut Command (`rag`) Setup

เราจะทำการสร้างคำสั่งย่อหรือ Shortcut ชื่อ `rag` บนเครื่องคอมพิวเตอร์ของคุณ โดยคำสั่งนี้จะทำการดึงเอาสภาพแวดล้อมจาก `.venv` ที่เตรียมไว้ขึ้นมารันไฟล์ `main.py` โดยอัตโนมัติ ทำให้คุณเรียกใช้ AI จากที่ไหนบนเครื่องก็ได้

### 5.1 ตั้งค่าผ่าน Bash / Zsh (สำหรับ macOS และ Linux)

1. เปิดไฟล์ตั้งค่าโปรไฟล์ของ Shell คุณ (ส่วนใหญ่คือ `~/.bashrc` หรือ `~/.zshrc`) ผ่านเอดิเตอร์:
```bash
nano ~/.zshrc

```


2. ใส่บรรทัด Alias ต่อไปนี้ไว้ที่ท้ายไฟล์ (แก้ไขเส้นทางให้ตรงกับที่อยู่โปรเจกต์จริงของคุณ):
```bash
alias rag="/absolute/path/to/antigravity-rag-cli/.venv/bin/python /absolute/path/to/antigravity-rag-cli/main.py start"
alias rag-sync="/absolute/path/to/antigravity-rag-cli/.venv/bin/python /absolute/path/to/antigravity-rag-cli/main.py sync"

```


3. บันทึกไฟล์ และสั่งรีโหลดโปรไฟล์:
```bash
source ~/.zshrc

```



### 5.2 ตั้งค่าผ่าน PowerShell (สำหรับ Windows)

1. เปิด PowerShell แล้วพิมพ์คำสั่งเปิดโปรไฟล์:
```powershell
notepad $PROFILE

```


2. ใส่ฟังก์ชันลัดต่อไปนี้ลงไปในไฟล์ (แก้ไขเส้นทางโฟลเดอร์ให้เป็นที่อยู่จริง):
```powershell
function Run-RagCLI {
    & "C:\path\to\antigravity-rag-cli\.venv\Scripts\python.exe" "C:\path\to\antigravity-rag-cli\main.py" "start"
}
function Run-RagSync {
    & "C:\path\to\antigravity-rag-cli\.venv\Scripts\python.exe" "C:\path\to\antigravity-rag-cli\main.py" "sync"
}
Set-Alias rag Run-RagCLI
Set-Alias rag-sync Run-RagSync

```


3. บันทึกไฟล์ แล้วเปิดหน้าต่าง PowerShell ใหม่

---

## 🎯 วิธีการใช้งานจริงประจำวัน (User Workflow)

เมื่อติดตั้งเสร็จเรียบร้อยแล้ว ทุกครั้งที่คุณต้องการใช้งานระบบ RAG นี้ คุณไม่จำเป็นต้องเปลี่ยนโฟลเดอร์ (cd) หรือพิมพ์คำสั่งยาวๆ อีกต่อไป เพียงทำตามขั้นตอนเหล่านี้:

1. **ส่งออก API Key ของคุณสู่ระบบ (Environment Variable):**
```bash
export TYPHOON_API_KEY="คีย์พาสเวิร์ดของคุณที่นี่"

```


2. **ทำการสั่ง Sync ข้อมูลเมื่อเพิ่มไฟล์ PDF ใหม่ในโฟลเดอร์:**
```bash
rag-sync

```


3. **พิมพ์คำสั่งสั้นเพื่อเข้าสู้หน้าต่างสนทนากับ Agent ค้นหาเอกสาร:**
```bash
rag

```


*ตัวโปรแกรมจะพาคุณเข้าสู่ลูปการ Prompt ถาม-ตอบทันทีโดยสืบค้นแยกโฟลเดอร์ผ่านคำสั่งตามที่ตั้งค่าไว้แบบอัตโนมัติครับ!*

```
--- 

คุณสามารถคัดลอกบล็อกมาร์กดาวน์ข้างต้น ไปวางในไฟล์เปล่าแล้วกดบันทึกเป็นชื่อไฟล์ `.md` ได้เลยครับ ตัวแบบแผนงานนี้สมบูรณ์และสามารถต่อยอดใช้งานได้จริงทันทีครับ!

```