import asyncio
from models import Submission, Question
from services.scoring_service.llm_scorer import score_with_llm

async def main():
    sub = Submission(submitted_html='<div></div>', submitted_css='', submitted_js='')
    q = Question(title='Test', description_html='<p>Test</p>')
    result = await score_with_llm(sub, q, 6, 6)
    print('RESULT:', result)

if __name__ == '__main__':
    asyncio.run(main())
