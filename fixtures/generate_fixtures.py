"""
Django fixture 생성 스크립트

articles.db의 posts_category와 posts_post 테이블 데이터를 읽어서
Django fixture JSON 파일로 변환합니다.

사용법:
    python fixtures/generate_fixtures.py
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# 현재 스크립트의 경로를 기준으로 설정
SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR.parent / "articles.db"
OUTPUT_DIR = SCRIPT_DIR

# 고정 설정
DEFAULT_AUTHOR_ID = 8592


def get_db_connection():
    """SQLite 데이터베이스 연결을 반환합니다."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_category_fixtures():
    """
    posts_category 테이블에서 Category fixture를 생성합니다.
    
    매핑:
    - gallery_id -> id (PK)
    - gallery_name -> name
    - category 컬럼은 무시
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT gallery_id, gallery_name FROM posts_category")
    rows = cursor.fetchall()
    
    fixtures = []
    for row in rows:
        fixture = {
            "model": "posts.category",
            "pk": row["gallery_id"],  # gallery_id를 pk(id)로 사용
            "fields": {
                "name": row["gallery_name"]
            }
        }
        fixtures.append(fixture)
    
    conn.close()
    return fixtures


def generate_post_fixtures():
    """
    posts_post 테이블에서 Post fixture를 생성합니다.
    
    매핑:
    - post_id -> id (PK, 숫자로 변환하여 사용)
    - gallery_id -> category (FK)
    - title -> title
    - content -> content
    - created_at -> created_at
    - author: 항상 id=8592인 User
    - is_nsfw: default False
    - is_profane: default False
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT post_id, gallery_id, title, content, created_at 
        FROM posts_post
    """)
    rows = cursor.fetchall()
    
    fixtures = []
    for idx, row in enumerate(rows, start=1):
        # created_at 처리 - None이면 현재 시간 사용
        created_at = row["created_at"]
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        fixture = {
            "model": "posts.post",
            "pk": idx,  # 순차적인 정수 ID 사용
            "fields": {
                "author": DEFAULT_AUTHOR_ID,
                "category": row["gallery_id"],  # FK로 gallery_id 사용
                "title": row["title"] or "",
                "content": row["content"] or "",
                "is_nsfw": False,  # default 값
                "is_profane": False,  # default 값
                "created_at": created_at
            }
        }
        fixtures.append(fixture)
    
    conn.close()
    return fixtures


def generate_comment_fixtures():
    """
    Comment fixture를 빈 리스트로 생성합니다.
    """
    return []


def generate_post_like_users_fixtures():
    """
    Post와 User의 like_users 중계 테이블 fixture를 빈 리스트로 생성합니다.
    """
    return []


def save_fixtures(fixtures, filename):
    """fixture를 JSON 파일로 저장합니다."""
    output_path = OUTPUT_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)
    print(f"✅ {filename} 생성 완료 ({len(fixtures)}개 레코드)")


def main():
    print("=" * 50)
    print("Django Fixture 생성 스크립트")
    print("=" * 50)
    print(f"DB 경로: {DB_PATH}")
    print(f"출력 경로: {OUTPUT_DIR}")
    print("-" * 50)
    
    # Category fixtures 생성
    print("\n📁 Category fixtures 생성 중...")
    category_fixtures = generate_category_fixtures()
    save_fixtures(category_fixtures, "categories.json")
    
    # Post fixtures 생성
    print("\n📁 Post fixtures 생성 중...")
    post_fixtures = generate_post_fixtures()
    save_fixtures(post_fixtures, "posts.json")
    
    # Comment fixtures (빈 리스트)
    print("\n📁 Comment fixtures 생성 중...")
    comment_fixtures = generate_comment_fixtures()
    save_fixtures(comment_fixtures, "comments.json")
    
    # Post-like_users 중계 테이블 fixtures (빈 리스트)
    print("\n📁 Post-like_users 중계 테이블 fixtures 생성 중...")
    like_users_fixtures = generate_post_like_users_fixtures()
    save_fixtures(like_users_fixtures, "post_like_users.json")
    
    print("\n" + "=" * 50)
    print("✅ 모든 fixture 생성 완료!")
    print("=" * 50)
    print("\n사용법:")
    print("  python manage.py loaddata fixtures/categories.json")
    print("  python manage.py loaddata fixtures/posts.json")
    print("  python manage.py loaddata fixtures/comments.json")
    print("  python manage.py loaddata fixtures/post_like_users.json")


if __name__ == "__main__":
    main()
