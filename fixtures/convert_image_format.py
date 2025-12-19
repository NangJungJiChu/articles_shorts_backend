"""
posts.json 파일의 이미지 표기를 마크다운 형식으로 변환하는 스크립트

변환:
  [IMAGE: /media/<id>.png] → ![](/media/<id>.png)
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
POSTS_FILE = SCRIPT_DIR / "posts.json"


def convert_image_format(content: str) -> str:
    """
    [IMAGE: /path/to/image.ext] 형식을 ![](/path/to/image.ext) 마크다운 형식으로 변환
    """
    # 정규식: [IMAGE: 경로] 패턴을 찾아서 ![](경로)로 변환
    pattern = r'\[IMAGE:\s*([^\]]+)\]'
    replacement = r'![](\1)'
    return re.sub(pattern, replacement, content)


def main():
    print("=" * 50)
    print("이미지 형식 변환 스크립트")
    print("=" * 50)
    print(f"대상 파일: {POSTS_FILE}")
    print("-" * 50)
    
    # posts.json 읽기
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)
    
    converted_count = 0
    image_count = 0
    
    for post in posts:
        content = post["fields"].get("content", "")
        
        # 변환 전 이미지 개수 카운트
        before_images = len(re.findall(r'\[IMAGE:', content))
        
        if before_images > 0:
            # 변환 수행
            new_content = convert_image_format(content)
            post["fields"]["content"] = new_content
            
            converted_count += 1
            image_count += before_images
    
    # 변환된 내용 저장
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 변환 완료!")
    print(f"   - 변환된 게시물 수: {converted_count}개")
    print(f"   - 변환된 이미지 수: {image_count}개")
    print("=" * 50)


if __name__ == "__main__":
    main()
