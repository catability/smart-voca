from typing import List, Dict, Any
import pandas as pd
import os
import sqlite3
from utils.logger import setup_logger
from config import DATABASE_PATH
from database.db_connection import DBConnection

# 2025-10-20 - 스마트 단어장 - 파일 처리 및 DB 초기화 유틸리티
# 파일 위치: utils/file_handler.py - v1
# 목적: CSV 파일 입출력 및 DB 스키마/초기 데이터 실행 기능 구현

LOGGER = setup_logger()

class FileHandler:
    """
    CSV 파일 임포트/엑스포트 및 데이터베이스 스키마 초기화 작업을 담당하는 유틸리티 클래스입니다.
    """
    
    def __init__(self):
        self.db_connector = DBConnection()

    # --- 1. DB 초기화 스크립트 실행 (최초 실행 시) ---
    
    def initialize_database(self, schema_file: str, init_data_file: str) -> bool:
        """
        DB 파일이 없거나 테이블이 없는 경우, 스키마 및 초기 데이터를 실행합니다.
        
        Args:
            schema_file (str): 테이블 정의 SQL 파일 경로 (e.g., 'database/schema.sql')
            init_data_file (str): 초기 설정 데이터 삽입 SQL 파일 경로 (e.g., 'database/init_data.sql')
        """
        db_exists = os.path.exists(DATABASE_PATH)
        
        # 1. 스키마 파일 실행 (테이블 생성)
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
                
            self.db_connector.connect()
            # executescript는 여러 개의 SQL문을 한 번에 실행하는 데 유용
            self.db_connector.executescripts(schema_sql)
            self.db_connector.commit()
            
            LOGGER.info(f"Database schema loaded from {schema_file}.")

        except FileNotFoundError:
            LOGGER.error(f"Schema file not found: {schema_file}")
            return False
        except sqlite3.Error as e:
            LOGGER.error(f"Error executing schema SQL: {e}")
            return False
        finally:
            self.db_connector.close()
            
        # 2. 초기 데이터 파일 실행 (설정값 삽입)
        try:
            if not db_exists:
                # DB가 새로 생성되었을 때만 초기 데이터 삽입
                with open(init_data_file, 'r', encoding='utf-8') as f:
                    init_sql = f.read()
                    
                self.db_connector.connect()
                self.db_connector.execute_script(init_sql)
                self.db_connector.commit()
                LOGGER.info(f"Initial data loaded from {init_data_file}.")
                
        except FileNotFoundError:
            LOGGER.warning(f"Initial data file not found: {init_data_file}. Skipping initial data load.")
            # 초기 데이터는 필수가 아닐 수 있으므로 경고 처리
        except sqlite3.Error as e:
            LOGGER.error(f"Error executing initial data SQL: {e}")
            return False
        finally:
            self.db_connector.close()
            
        return True

    # --- 2. CSV Import/Export ---

    def import_words_from_csv(self, file_path: str, word_model) -> List[Dict[str, Any]]:
        """
        CSV 파일을 읽어 단어 데이터(Dict 리스트)로 변환하고, WordModel을 사용하여 DB에 저장합니다.
        반환값: {total, added, updated, skipped}
        """
        # 기존 CSV 파싱 로직 (word_list를 얻는 부분)
        # ----------------------------------------------------
        try:
            # df = pd.read_csv(file_path, encoding='utf-8') 
            # ... (인코딩 처리 및 필수 컬럼 검사 로직 유지)
            # ... (최종적으로 word_list = df[final_cols].fillna(...).to_dict('records') 얻음)
            
            # 가정을 위해 위 기존 코드를 임시로 포함:
            try:
                df = pd.read_csv(file_path, encoding='utf-8') 
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='cp949')
            
            required_cols = ['word_text', 'meaning_ko', 'category']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV 파일에 필수 컬럼({', '.join(required_cols)})이 누락되었습니다.")

            export_cols = required_cols + ['memo', 'is_favorite']
            final_cols = [col for col in export_cols if col in df.columns]
            word_list = df[final_cols].fillna({'memo': '', 'is_favorite': 0}).to_dict('records')
            for item in word_list:
                if 'is_favorite' in item:
                    item['is_favorite'] = int(item['is_favorite']) if pd.notna(item['is_favorite']) else 0
            # ----------------------------------------------------
            
            if not word_list:
                return {'total': 0, 'added': 0, 'updated': 0, 'skipped': 0}

            # ✨ 새로운 DB 저장 로직 (WordModel 사용) ✨
            total = len(word_list)
            added = 0
            updated = 0
            skipped = 0
            
            for idx, word_data in enumerate(word_list):
                word_text = word_data['word_text']
                
                # 1. 단어가 이미 존재하는지 확인
                existing_word = word_model.get_word_by_text(word_text) # WordModel에 get_word_by_text 필요하다고 가정
                
                if existing_word:
                    # 2. 존재하면 업데이트
                    if word_model.update_word_by_text(word_text, word_data): # WordModel에 update_word_by_text 필요
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # 3. 없으면 삽입
                    if word_model.insert_word(word_data):
                        added += 1
                    else:
                        skipped += 1
                        
            LOGGER.info(f"CSV import successful. Total: {total}, Added: {added}, Updated: {updated}")
            return {'total': total, 'added': added, 'updated': updated, 'skipped': skipped}

        except Exception as e:
            LOGGER.error(f"Error during CSV import to DB: {e}")
            return None # 실패 시 None 반환

    def export_words_to_csv(self, file_path: str, data: List[Dict[str, Any]]) -> bool:
        """
        단어 데이터(Dict 리스트)를 CSV 파일로 저장합니다. (F5)
        """
        if not data:
            LOGGER.warning("Export requested with empty data list.")
            return False
            
        try:
            df = pd.DataFrame(data)
            # UTF-8 인코딩 및 BOM 추가로 엑셀에서 한글 깨짐 방지
            df.to_csv(file_path, index=False, encoding='utf-8-sig') 
            LOGGER.info(f"Words exported successfully to {file_path}")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to export words to CSV: {e}")
            return False