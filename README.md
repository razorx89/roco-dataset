Radiology Objects in COntext (ROCO): A Multimodal Image Dataset
===============================================================

This repository contains the *Radiology Objects in COntext (ROCO)* dataset, a large-scale medical and multimodal imaging dataset. The listed images are from publications available on the PubMed Central Open Access FTP mirror, which were automatically detected as non-compound and either radiology or non-radiology. Each image is distributed as a download link, together with its caption. Additionally, keywords extracted from the image caption, as well as the corresponding UMLS Semantic Types (SemTypes) and UMLS Concept Unique Identifiers (CUIs) are available. The dataset could be used to build generative models for image captioning, classification models for image categorization and tagging or content-based image retrieval systems.

Get started
-----------
To download the images, clone the repository and run

```bash
python scripts/fetch.py
```

Citation
--------
If you use this dataset for your own research, please cite the following paper:
> O. Pelka, S. Koitka, J. Rückert, F. Nensa, C.M. Friedrich,  
> "__Radiology Objects in COntext (ROCO): A Multimodal Image Dataset__".  
> MICCAI Workshop on Large-scale Annotation of Biomedical Data and Expert Label Synthesis (LABELS) 2018, September 16, 2018, Granada, Spain. Lecture Notes on Computer Science (LNCS), vol. 11043, pp. 180-189, Springer Cham, 2018.  
> doi: [10.1007/978-3-030-01364-6_20](https://doi.org/10.1007/978-3-030-01364-6_20)
