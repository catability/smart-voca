-- 2025-10-20 - 스마트 단어장 - 초기 설정 데이터 삽입
-- 파일 위치: database/init_data.sql - v1

-- 1. 기본 사용자 설정 삽입
-- user_settings 테이블에 config.py에 정의된 기본값 삽입
INSERT OR IGNORE INTO user_settings (setting_key, setting_value, setting_type, description, modified_date) VALUES
('theme_mode', 'light', 'string', 'UI 테마 모드: light 또는 dark', datetime('now')),
('default_quiz_count', '10', 'integer', '기본 퀴즈 문항 수', datetime('now')),
('review_interval_days', '3', 'integer', '기본 복습 주기 (일)', datetime('now')),
('max_memo_length', '200', 'integer', '단어별 메모 최대 길이', datetime('now')),
('language_pair', 'en-ko', 'string', '학습 방향: en-ko 또는 ko-en', datetime('now'));

-- 참고: 초기 단어 데이터는 CSV 임포트를 통해 입력하거나, 별도의 `initial_words.sql` 파일로 관리할 수 있습니다.
-- 현재는 핵심 설정 데이터만 포함합니다.