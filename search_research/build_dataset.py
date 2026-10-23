"""Verified, versioned question splits. Gold stays outside worker directories."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dataset_v1'
FILES = {x.parent.name: x.relative_to(DATA/'corpus').as_posix() for x in (DATA/'corpus').glob('*/*.ipynb')}

def field(answer, chapter, cell, quote, aliases=None):
    source=''.join(json.loads((DATA/'corpus'/FILES[chapter]).read_text(encoding='utf-8'))['cells'][cell]['source'])
    assert quote in source, (chapter,cell,quote)
    return {'answer':str(answer),'aliases':aliases or [],'file':FILES[chapter],'cell':cell,'quote':quote}

def task(id, split, chapters, question, facts):
    return {'id':id,'split':split,'chapters':chapters,'question':question,'facts':facts}

TASKS=[
 task('p_absent','practice',['chapter04'],
      "Find the active LogisticRegression configuration that sets class_weight='balanced'. Return field class_weight. If that setting is not present in this notebook, report unknown rather than guessing.",
      {'class_weight':{'answer':'unknown','aliases':[], 'absent':True,'file':FILES['chapter04'],'forbidden_pattern':"class_weight"}}),
 task('p_classification','practice',['chapter04'],
      'In the supervised embedding-based classification example, identify the embedding model, classifier class, and random-state value. Return fields embedding_model, classifier, random_state.',
      {'embedding_model':field('sentence-transformers/all-mpnet-base-v2','chapter04',14,"SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"),
       'classifier':field('LogisticRegression','chapter04',16,'LogisticRegression(random_state=42)'),
       'random_state':field('42','chapter04',16,'LogisticRegression(random_state=42)')}),
 task('p_denoising','practice',['chapter10'],
      'In the unsupervised denoising embedding example, identify the loss class, the optional deletion ratio, and whether that optional ratio is active or commented out. Return fields loss, deletion_ratio, ratio_status.',
      {'loss':field('DenoisingAutoEncoderLoss','chapter10',74,'train_loss = losses.DenoisingAutoEncoderLoss(', ['losses.DenoisingAutoEncoderLoss']),
       'deletion_ratio':field('0.6','chapter10',71,'del_ratio=0.6'),
       'ratio_status':field('commented out','chapter10',71,'# # Choose a different deletion ratio\n# flat_sentences = list(set(flat_sentences))', ['commented','inactive'])}),
 task('e_clustering','evaluation',['chapter05'],
      'For the initial document clustering pipeline, find the dimensionality-reduction output size, its distance metric, and the density clusterer minimum cluster size. Return fields dimensions, reduction_metric, min_cluster_size.',
      {'dimensions':field('5','chapter05',10,'n_components=5'),
       'reduction_metric':field('cosine','chapter05',10,"metric='cosine'"),
       'min_cluster_size':field('50','chapter05',12,'min_cluster_size=50')}),
 task('e_retrieval','evaluation',['chapter08'],
      'Compare the function definitions for keyword search and keyword-plus-reranking. What is the default candidate count for each, and the dense FAISS index class? Return fields keyword_candidates, reranking_candidates, index_class.',
      {'keyword_candidates':field('15','chapter08',16,'def keyword_search(query, top_k=3, num_candidates=15):'),
       'reranking_candidates':field('10','chapter08',23,'def keyword_and_reranking_search(query, top_k=3, num_candidates=10):'),
       'index_class':field('IndexFlatL2','chapter08',10,'index = faiss.IndexFlatL2(dim)',['faiss.IndexFlatL2'])}),
 task('e_fewshot','evaluation',['chapter11'],
      'In the active SetFit few-shot example, find samples per class, training epochs, and contrastive pair iterations. Ignore the commented older trainer example. Return fields samples_per_class, epochs, iterations.',
      {'samples_per_class':field('16','chapter11',32,'num_samples=16'),
       'epochs':field('3','chapter11',34,'num_epochs=3'),
       'iterations':field('20','chapter11',34,'num_iterations=20')})
]

def build():
    # Validate all gold evidence before freezing the split.
    for t in TASKS:
        for f in t['facts'].values():
            if f.get('absent'):
                nb=json.loads((DATA/'corpus'/f['file']).read_text(encoding='utf-8'))
                assert not any(f['forbidden_pattern'] in ''.join(c['source']) for c in nb['cells'])
    obj={'version':'1.0.2','cell_numbering':'zero-based','tasks':TASKS,
         'limitations':['Small hand-authored benchmark; human audit recommended.',
                        'Public notebooks may have appeared in model training.',
                        'Practice and evaluation source chapters are disjoint.']}
    (DATA/'tasks.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
    print('Verified',len(TASKS),'tasks and',sum(len(t['facts']) for t in TASKS),'source evidence anchors')

if __name__=='__main__': build()
