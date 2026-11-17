# 도구 사용법 (AI용)

스킬 폴더의 `bin/cafe-writer`를 실행한다. 경로 인수는 현재 작업 폴더 기준. `--out`은 아직 없는 폴더여야 한다. 학생에게 이 명령을 보여 주지 않는다.

```
cafe-writer doctor
cafe-writer brief --keywords '초보자를 위한 카페 운영 팁' --out work/keyword-001
cafe-writer brief --source-file source.txt --audience '카페 운영자' --goal '신입 회원 안내' --out work/job-001
# AI가 work/job-001/manuscript.md 작성
cafe-writer build --manuscript work/job-001/manuscript.md --brief work/job-001/brief.json --title '제목' --cafe-url <카페 주소> --board '게시판 이름' --image 이미지1.png --image 이미지2.png --out work/draft-001
cafe-writer validate work/draft-001/manifest.json
```

- `brief`: 키워드만으로도 된다. `--source-file`, `--audience`, `--goal`, `--tone`은 선택. 도구는 AI를 부르지 않고, 글을 쓰는 AI에게 줄 요청문(`writer-request.md`)을 만든다.
- `build` 선택 인수: `--image`(이미지마다 반복), `--cta 문구 --cta-url 주소`(둘 같이), `--source-url`(원문 링크 표기), `--brief`(작성 때 쓴 원문 묶기).
- 성공하면 `manifest.json`, `manuscript.md`, `body.txt`, `preview.html`과 사용한 이미지가 나온다. HTML은 검토용이다. 네이버 편집기에 넣는 기능과 발행은 포함하지 않는다.
- 출력은 JSON. 종료 0 성공, 1 검증 실패, 2 잘못된 입력·누락 파일. 해시는 변경 탐지용이지 서명이나 승인 증거가 아니다.
