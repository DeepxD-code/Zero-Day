from pathlib import Path
import re

source = Path('docs/literature_review_nine_papers_humanized_v2.txt')
target = Path('docs/literature_review_nine_papers_humanized_final.txt')
text = source.read_text(encoding='utf-8')
replacements = {
    'synthesises': 'combines', 'synthesized': 'combined', 'taxonomy': 'classification',
    'interpretability void': 'lack of clear explanations',
    'standardisation deficit': 'lack of common standards',
    'encrypted-payload blind spot': 'difficulty with encrypted traffic',
    'graph-native': 'based on the graph itself',
    'chronological temporal integration': 'keeping the time order',
    'cross-plane attacks': 'attacks across different data sources',
    'resource-aware embeddings': 'embeddings that work on limited hardware',
    'longitudinal deployment': 'long-term testing',
    'human-centred': 'human-focused',
    'post-hoc': 'after-the-fact',
    'inner-product decoding': 'inner-product scoring',
    'parameter costs': 'extra memory and computing costs',
    'headline scores': 'high scores',
    'rare-event detection': 'finding rare events',
    'enterprise data': 'real organisational data',
    'study-design issues': 'issues in the study design',
    'Publication rating:': 'Overall assessment:',
    'Overall assessment: 7/10 as a review': 'Overall assessment: 7/10',
    'Overall assessment: 8/10, because': 'Overall assessment: 8/10. The paper is strong because',
    'Overall assessment: 7/10 based on the supplied material;': 'Overall assessment: 7/10. Based on the supplied material,',
    'while retaining keeping the time order': 'while keeping the time order',
    'Significant scope remains in': 'There is still room for',
    'common protocols, cross-dataset evaluation': 'common protocols, testing across datasets',
    'explanation faithfulness tests': 'tests of whether explanations are accurate',
    'the classification is valuable': 'the grouping is useful',
    'bounded by after-the-fact explanation limitations': 'limited by the weaknesses of after-the-fact explanations',
}
for old, new in replacements.items():
    text = text.replace(old, new)
text = re.sub(r'\bconsiderable\b', 'quite large', text)
text = re.sub(r'\bsubstantial\b', 'a lot of', text)
text = text.replace('—', '-').replace('–', '-').replace('‑', '-').replace('’', "'").replace('“', '"').replace('”', '"')
text = re.sub(r' +', ' ', text)
target.write_text(text, encoding='utf-8')
print(target)
