from pathlib import Path
import re

source = Path('docs/literature_review_nine_papers_humanized.txt')
target = Path('docs/literature_review_nine_papers_humanized_v2.txt')
text = source.read_text(encoding='utf-8')

replacements = {
    'Each paper is discussed using the same points:': 'For each paper, the review covers the same basic questions:',
    'The reported results come from the supplied notes and should be checked against the original papers before submission.':
        'The results below come from the supplied notes, so the original papers should still be checked before submission.',
    'A clear strength is that the design addresses a real systems constraint rather than only adding model complexity.':
        'One good aspect of the design is that it tackles a real scaling problem instead of only making the model larger.',
    'The main weaknesses are practical and related to the study design.':
        'There are, however, some practical weaknesses and study-design issues.',
    'The work also leaves the relationship between scalability, threshold calibration, and analyst workload insufficiently resolved.':
        'It is still not clear how the system would balance scale, threshold choice, and the amount of work left for analysts.',
    'There is still room to study: continuous-time updates, drift-aware thresholds, structural adversarial defence, calibrated uncertainty, and replication on independent enterprise data are open problems.':
        'Further work could look at continuous-time updates, changing network behaviour, structural attacks, uncertainty estimates, and tests on independent enterprise data.',
    'This paper asks whether GNN-based NIDS can be evaded':
        'The second paper asks whether a GNN-based NIDS can be bypassed',
    'Its main strength is that the attack model is realistic:':
        'One thing this study does well is use a realistic attack model:',
    'The paper gives the field a useful threat model, but it mainly improves how GNN security is tested. It does not improve the detector itself.':
        'This is useful for testing GNN security, although it does not make the detector itself better.',
    'This review brings together work on': 'The third paper brings together research on',
    'Its value is the comparison itself, not a new detection model.':
        'The value here is the organised comparison, rather than a new detection model.',
    'The biggest problem is that the studies are difficult to compare.':
        'The main issue is that the studies are not easy to compare fairly.',
    'So, the review is useful as a map of the field, but it does not prove that one architecture is always best.':
        'This makes the review useful as a map of the field, but it does not show that one architecture is always the best choice.',
    'The main improvement is the way the evidence is organised:':
        'Its main contribution is the way it organises the evidence:',
    'This paper proposes XAI-IDR to deal with':
        'The fourth paper presents XAI-IDR as a way to deal with',
    'The key idea is the dual gate:':
        'The central idea is a two-step safety check:',
    'The focus on real security work and human review is a strength.':
        'The focus on actual security work and human review makes the proposal easier to understand.',
    'The response-gating idea is useful, but more work is needed on':
        'The response-gating idea is useful, but the study still needs stronger evidence about',
    'This paper looks at a label-leakage problem in':
        'The fifth paper looks at a possible label-leakage problem in',
    'This matters because preprocessing can quietly introduce supervision into an apparently unsupervised experiment.':
        'This matters because preprocessing can add label information even when the experiment is described as unsupervised.',
    'The main strength is that it points out a common but easy-to-miss problem:':
        'The useful point made by this paper is that it draws attention to a common but easy-to-miss problem:',
    'This study compares two post-hoc explanation methods for an MLP-based IDS.':
        'The sixth paper compares two post-hoc explanation methods on an MLP-based IDS.',
    'It is useful because it tests the explanations instead of assuming that every explanation is reliable.':
        'This is helpful because it tests the explanations rather than assuming they are reliable.',
    'The main improvement is about interpretation, not detection:':
        'The contribution is mainly about making decisions easier to inspect, not about improving detection:',
    'This paper reviews deep-learning methods used in User and Entity Behavior Analytics.':
        'The seventh paper reviews deep-learning methods used in User and Entity Behavior Analytics.',
    'Its strengths are its wide coverage and its discussion of practical limits.':
        'The review is useful because it covers many model types and also discusses their practical limits.',
    'This paper tries to make anomaly results easier to understand by turning them into natural-language explanations.':
        'The eighth paper tries to make anomaly results easier to understand by turning them into plain-language explanations.',
    'Its main strength is that it focuses on what an analyst can understand and use.':
        'The main strength is its focus on what a security analyst can actually understand and use.',
    'This study checks whether published graph-based intrusion-detection results can be reproduced.':
        'The ninth paper checks whether published graph-based intrusion-detection results can actually be reproduced.',
    'The strongest contribution is its focus on checking the evidence:':
        'Its strongest contribution is that it checks the evidence behind published results:',
    'This is important for the field because':
        'This matters because',
    'Overall, the papers leave several useful questions open.':
        'Overall, the papers leave several practical questions open.',
    'Overall rating:': 'Overall assessment:',
}
for old, new in replacements.items():
    text = text.replace(old, new)

for old, new in {
    'The supplied notes report': 'The review notes report',
    'The supplied report gives': 'The review notes give',
    'The supplied review describes': 'The review notes describe',
    'The supplied review states': 'The review notes state',
    'The supplied material': 'The supplied notes',
    'It also provides': 'The model also provides',
    'However,': 'Still,',
    'Although': 'Even though',
    'In terms of improvement,': 'As an improvement,',
}.items():
    text = text.replace(old, new)

text = re.sub(r'\bPublication rating:', 'Overall assessment:', text)
text = text.replace('—', '-').replace('–', '-').replace('‑', '-').replace('’', "'").replace('“', '"').replace('”', '"')
text = re.sub(r' +', ' ', text)
target.write_text(text, encoding='utf-8')
print(target)
