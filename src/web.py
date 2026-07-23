from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from answer import FALLBACK_ANSWER, answer_query, setup_chat_client
from ingest import setup_embedding_client

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
DATA_DIR = ROOT_DIR / "data"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


class SourceItem(BaseModel):
    name: str
    title: str


def display_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def split_answer_and_sources(result: str) -> tuple[str, list[str]]:
    marker = "\n\nSources: "
    if marker not in result:
        return result, []
    answer, source_text = result.rsplit(marker, maxsplit=1)
    sources = [source.strip() for source in source_text.split(",") if source.strip()]
    return answer, sources


class LocalRagService:
    def __init__(self) -> None:
        self.embedding_model = None
        self.embedding_client = None
        self.chat_model = None
        self.chat_client = None
        self.lock = Lock()

    @property
    def ready(self) -> bool:
        return self.embedding_client is not None and self.chat_client is not None

    def load(self) -> None:
        if self.ready:
            return
        self.embedding_model, self.embedding_client = setup_embedding_client()
        try:
            self.chat_model, self.chat_client = setup_chat_client()
        except Exception:
            self.embedding_model.unload()
            self.embedding_model = None
            self.embedding_client = None
            raise

    def ask(self, question: str) -> AskResponse:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Question cannot be empty.")
        with self.lock:
            self.load()
            result = answer_query(
                cleaned_question,
                self.embedding_client,
                self.chat_client,
            )
        answer, sources = split_answer_and_sources(result)
        if answer == FALLBACK_ANSWER:
            sources = []
        return AskResponse(answer=answer, sources=sources)

    def close(self) -> None:
        if self.chat_model is not None:
            self.chat_model.unload()
        if self.embedding_model is not None:
            self.embedding_model.unload()
        self.embedding_model = None
        self.embedding_client = None
        self.chat_model = None
        self.chat_client = None


service = LocalRagService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    service.close()


app = FastAPI(
    title="Foundry Local Guide API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ready" if service.ready else "idle"}


@app.get("/api/sources", response_model=list[SourceItem])
def sources() -> list[SourceItem]:
    paths = sorted(list(DATA_DIR.glob("*.md")) + list(DATA_DIR.glob("*.txt")))
    return [SourceItem(name=path.name, title=display_title(path)) for path in paths]


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        return service.ask(request.question)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="The local AI models could not answer the question.",
        ) from error


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
