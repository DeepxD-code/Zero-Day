from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

source = 'docs/literature_review_nine_papers_google_sanitized.docx'
target = 'docs/literature_review_nine_papers_plain.txt'
doc = Document(source)
items = []
for child in doc.element.body.iterchildren():
    if child.tag == qn('w:p'):
        items.append(Paragraph(child, doc).text)
    elif child.tag == qn('w:tbl'):
        table = Table(child, doc)
        items.append('\n'.join(' | '.join(cell.text for cell in row.cells) for row in table.rows))
with open(target, 'w', encoding='utf-8') as handle:
    handle.write('\n\n'.join(item for item in items if item.strip()))
print(target)
