from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.router import setup_routers
from config.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 로직"""
    # Startup
    print("🚀 Starting HexaCore AI Server...")

    # 데이터베이스 테이블 생성
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

    yield

    # Shutdown
    print("🛑 Shutting down HexaCore AI Server...")
    engine.dispose()
    print("✅ Database connections closed")


app = FastAPI(
    title="Hexa AI",
    description="MBTI 서비스",
    version="0.1.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:3000",  # Next.js 프론트 엔드 URL
    "https://hexa-frontend.vercel.app",  # Vercel 배포 URL
    "https://hexa-frontend-chi.vercel.app",  # Vercel 배포 URL (chi)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 정확한 origin만 허용
    allow_credentials=True,      # 쿠키 허용
    allow_methods=["*"],         # 모든 HTTP 메서드 허용
    allow_headers=["*"],         # 모든 헤더 허용
)

# Setup all routers
setup_routers(app)

@app.get("/health")
async def health_check():
    """서버 상태 체크"""
    return {
        "status": "healthy",
        "database": "ok"
    }

