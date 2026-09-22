from pathlib import Path
import re

source = Path('docs/literature_review_nine_papers_plain.txt')
target = Path('docs/literature_review_nine_papers_humanized.txt')
text = source.read_text(encoding='utf-8')

replacements = {
    'LITERATURE REVIEW: PAPER-BY-PAPER ANALYSIS': 'Literature Review of Nine Papers',
    'Supervisor Review Draft | Nine Supplied Sources': 'Paper-by-paper review draft',
    'Scope note: This draft is based only on the nine supplied paper-review files, reference notes, and the linked arXiv record. Project-specific comparisons, team roles, proposed architecture, and project results have been intentionally excluded.':
        'Scope note: This review uses only the nine sources provided. It does not include project details or proposed system results.',
    'How to read this chapter': 'About this review',
    'Each paper is analysed using the same review dimensions:': 'Each paper is discussed using the same points:',
    'Reported metrics are retained only where they were present in the supplied material. They should be checked against the original publications before final submission.':
        'The reported results come from the supplied notes and should be checked against the original papers before submission.',
    'IEEE-style citation numbers are assigned in order of first appearance and remain unchanged throughout the chapter. The bracketed numbers in this draft, such as [1] and [2], refer to the reference list at the end.':
        'The numbers in square brackets, such as [1] and [2], refer to the reference list at the end.',
    'addresses the scalability bottleneck': 'looks at the problem of scale',
    'The central improvement is to': 'The main change is to',
    'The most important strength is that': 'A clear strength is that',
    'The main weaknesses are operational and methodological.': 'The main weaknesses are practical and related to the study design.',
    'The remaining research scope is significant:': 'There is still room to study:',
    'Publication strength:': 'Publication rating:',
    'This paper studies whether': 'This paper asks whether',
    'The methodology imposes four realistic constraints:': 'The authors set four practical limits:',
    'Its main strength is realism:': 'Its main strength is that the attack model is realistic:',
    'The paper introduces an important threat model, but its improvements are significant mainly for evaluating GNN security, not for improving detection itself.':
        'The paper gives the field a useful threat model, but it mainly improves how GNN security is tested. It does not improve the detector itself.',
    'This systematic review addresses fragmentation in': 'This review brings together work on',
    'Its core value is comparative structure rather than a new detection model.': 'Its value is the comparison itself, not a new detection model.',
    'The major weakness is comparability.': 'The biggest problem is that the studies are difficult to compare.',
    'Therefore, its conclusions are useful as a research map rather than as proof that one architecture is universally superior.':
        'So, the review is useful as a map of the field, but it does not prove that one architecture is always best.',
    'The improvements are organisational and methodological:': 'The main improvement is the way the evidence is organised:',
    'This paper proposes XAI-IDR to address': 'This paper proposes XAI-IDR to deal with',
    'The research problem is not simply whether attacks can be classified, but whether automated containment can be made safe enough for security operations':
        'The authors are concerned not only with detection, but also with whether automated containment can be used safely',
    'Its strongest contribution is the dual gate:': 'The key idea is the dual gate:',
    'The operational framing and human-in-the-loop policy are clear strengths.': 'The focus on real security work and human review is a strength.',
    'The improvement is significant for safe response orchestration, but substantial research remains in':
        'The response-gating idea is useful, but more work is needed on',
    'This paper focuses on the label dependence hidden inside': 'This paper looks at a label-leakage problem in',
    'The proposed direction is in-context self-supervised pre-training with dense representations so that useful feature structure can be learned without relying on target labels.':
        'The authors use self-supervised pre-training so that the model can learn useful representations without using attack labels during preprocessing.',
    'This is a strong conceptual improvement because it addresses the boundary between preprocessing and supervision.':
        'This matters because preprocessing can quietly introduce supervision into an apparently unsupervised experiment.',
    'The key strength is that it identifies a subtle but important methodological error:':
        'The main strength is that it points out a common but easy-to-miss problem:',
    'This study examines whether post-hoc explainability methods can make an MLP-based IDS understandable to analysts.':
        'This study compares two post-hoc explanation methods for an MLP-based IDS.',
    'Its value is that it treats explanation as an empirical object rather than assuming that any attribution method is automatically trustworthy.':
        'It is useful because it tests the explanations instead of assuming that every explanation is reliable.',
    'The improvement is interpretive rather than predictive:': 'The main improvement is about interpretation, not detection:',
    'This paper is a systematic review of deep-learning-based User and Entity Behavior Analytics.':
        'This paper reviews deep-learning methods used in User and Entity Behavior Analytics.',
    'Its strength is the broad taxonomy and explicit discussion of operational constraints.':
        'Its strengths are its wide coverage and its discussion of practical limits.',
    'This paper moves beyond feature-importance scores by generating natural-language explanations for anomaly-detection results.':
        'This paper tries to make anomaly results easier to understand by turning them into natural-language explanations.',
    'Its main strength is usability and a clear focus on the analyst rather than only the model developer.':
        'Its main strength is that it focuses on what an analyst can understand and use.',
    'This study asks whether state-of-the-art graph intrusion-detection results can be reproduced and replicated reliably.':
        'This study checks whether published graph-based intrusion-detection results can be reproduced.',
    'The strongest contribution is methodological honesty:': 'The strongest contribution is its focus on checking the evidence:',
    'The improvement is highly significant for the field because': 'This is important for the field because',
    'Across the nine sources, three recurring issues dominate.': 'Across the nine papers, three issues appear repeatedly.',
    'Taken together, the papers leave meaningful research space.': 'Overall, the papers leave several useful questions open.',
}

for old, new in replacements.items():
    text = text.replace(old, new)

for old, new in {
    'demonstrates': 'shows', 'demonstrated': 'showed', 'utilizes': 'uses', 'utilize': 'use',
    'comprehensive': 'broad', 'heterogeneous': 'different', 'substantial': 'considerable',
    'methodology': 'method', 'methodological': 'related to the study design',
    'operational': 'practical', 'empirical': 'experimental', 'conceptual': 'main',
    'significant': 'important', 'therefore': 'so', 'Furthermore': 'Also',
    'In addition': 'Also', 'mitigate': 'reduce', 'facilitate': 'help',
}.items():
    text = re.sub(r'\b' + re.escape(old) + r'\b', new, text, flags=re.IGNORECASE if old[0].isupper() else 0)

text = text.replace('—', '-').replace('–', '-').replace('‑', '-').replace('’', "'").replace('“', '"').replace('”', '"')
text = re.sub(r' +', ' ', text)
target.write_text(text, encoding='utf-8')
print(target)
