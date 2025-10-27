-- 2025-10-20 - 스마트 단어장 - 데이터베이스 스키마 정의
-- 파일 위치: database/schema.sql - v1

-- 공통 날짜 형식: TEXT (ISO 8601 'YYYY-MM-DD HH:MM:SS')
-- 공통 삭제 여부: INTEGER (0: 미삭제, 1: 삭제)

-- 1. 단어 정보 테이블 (words)
CREATE TABLE IF NOT EXISTS words (
    word_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    word_text       TEXT NOT NULL UNIQUE,      -- 단어 (예: 'apple')
    meaning_ko      TEXT NOT NULL,             -- 한국어 의미 (예: '사과')
    category        TEXT NOT NULL,             -- 카테고리 (예: '수능', '토익', '기본')
    memo            TEXT,                      -- 사용자 메모
    is_favorite     INTEGER DEFAULT 0,         -- 즐겨찾기 여부 (0:false, 1:true)
    created_date    TEXT NOT NULL,
    modified_date   TEXT NOT NULL,
    is_deleted      INTEGER DEFAULT 0
);

-- 2. 학습 세션 테이블 (learning_sessions)
CREATE TABLE IF NOT EXISTS learning_sessions (
    session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type    TEXT NOT NULL,             -- 세션 유형 (예: '암기', '시험')
    session_mode    TEXT NOT NULL,             -- 학습 모드 (예: '랜덤', '오답률', '순차')
    start_time      TEXT NOT NULL,             -- 시작 시간
    end_time        TEXT,                      -- 종료 시간
    total_words     INTEGER NOT NULL,          -- 총 학습 단어 수
    correct_count   INTEGER DEFAULT 0,         -- 정답 수
    wrong_count     INTEGER DEFAULT 0,         -- 오답 수
    is_completed    INTEGER DEFAULT 0          -- 완료 여부 (0:진행중, 1:완료)
);

-- 3. 학습 이력 테이블 (learning_history)
CREATE TABLE IF NOT EXISTS learning_history (
    history_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL,
    word_id         INTEGER NOT NULL,
    is_correct      INTEGER NOT NULL,          -- 정답 여부 (0:오답, 1:정답)
    response_time   REAL,                      -- 답변 시간 (초 단위)
    learning_date   TEXT NOT NULL,
    
    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id),
    FOREIGN KEY (word_id) REFERENCES words(word_id)
);

-- 4. 단어 통계 테이블 (word_statistics)
CREATE TABLE IF NOT EXISTS word_statistics (
    stats_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id         INTEGER NOT NULL UNIQUE,   -- 단어 ID (words 테이블에 종속)
    total_attempts  INTEGER DEFAULT 0,         -- 총 시도 횟수
    correct_count   INTEGER DEFAULT 0,         -- 총 정답 횟수
    last_review     TEXT,                      -- 마지막 학습 일시
    next_review     TEXT,                      -- 다음 복습 추천 일시 (Spaced Repetition System 기반)
    mastery_level   INTEGER DEFAULT 0,         -- 숙련도 레벨 (0~5)
    
    FOREIGN KEY (word_id) REFERENCES words(word_id)
);

-- 5. 시험 이력 테이블 (exam_history)
CREATE TABLE IF NOT EXISTS exam_history (
    exam_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_date       TEXT NOT NULL,
    exam_type       TEXT NOT NULL,             -- 시험 유형 (예: '단답형', '객관식')
    total_questions INTEGER NOT NULL,
    score           REAL NOT NULL,             -- 점수 (예: 85.5)
    duration_sec    INTEGER,                   -- 소요 시간 (초)
    is_deleted      INTEGER DEFAULT 0
);

-- 6. 시험 문제 상세 테이블 (exam_questions) - 오답 관리를 위해 시험마다 문제를 기록
CREATE TABLE IF NOT EXISTS exam_questions (
    question_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id         INTEGER NOT NULL,
    word_id         INTEGER NOT NULL,
    question_text   TEXT NOT NULL,             -- 문제 (단어)
    correct_answer  TEXT NOT NULL,             -- 정답 (의미)
    user_answer     TEXT,                      -- 사용자 답변
    is_correct      INTEGER NOT NULL,          -- 정답 여부 (0:오답, 1:정답)
    
    FOREIGN KEY (exam_id) REFERENCES exam_history(exam_id),
    FOREIGN KEY (word_id) REFERENCES words(word_id)
);

-- 7. 오답 노트 테이블 (wrong_note) - 가장 최근의 오답 기록을 관리하여 복습 대상 선정
CREATE TABLE IF NOT EXISTS wrong_note (
    note_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id         INTEGER NOT NULL UNIQUE,   -- 단어 ID
    latest_exam_id  INTEGER,                   -- 가장 최근에 틀린 시험 ID (참조용)
    wrong_count     INTEGER DEFAULT 1,         -- 누적 오답 횟수
    last_wrong_date TEXT NOT NULL,             -- 마지막으로 틀린 날짜
    
    FOREIGN KEY (word_id) REFERENCES words(word_id)
);

-- 8. 사용자 설정 테이블 (user_settings)
CREATE TABLE IF NOT EXISTS user_settings (
    setting_key     TEXT PRIMARY KEY NOT NULL, -- 설정 키 (예: 'theme_mode')
    setting_value   TEXT NOT NULL,             -- 설정 값 (예: 'dark')
    setting_type    TEXT,                      -- 값의 타입 (예: 'string', 'integer')
    description     TEXT,                      -- 설정 설명
    modified_date   TEXT NOT NULL
);