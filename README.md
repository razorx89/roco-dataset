Radiology Objects in COntext (ROCO): A Multimodal Image Dataset
===============================================================

This repository contains the *Radiology Objects in COntext (ROCO)* dataset, a large-scale medical and multimodal imaging dataset. The listed images are from publications available on the PubMed Central Open Access FTP mirror, which were automatically detected as non-compound and either radiology or non-radiology. Each image is distributed as a download link, together with its caption. Additionally, keywords extracted from the image caption, as well as the corresponding UMLS Semantic Types (SemTypes) and UMLS Concept Unique Identifiers (CUIs) are available. The dataset could be used to build generative models for image captioning, classification models for image categorization and tagging or content-based image retrieval systems.

A subset of the ROCO dataset is used as development data for the Concept Detection Task at [ImageCLEF 2019](https://www.imageclef.org/2019). Further information regarding the task description, submission dates, and publication opportunities can be found at [ImageCLEFmed Caption 2019](https://www.imageclef.org/2019/medical/caption) and [CrowdAI](https://www.crowdai.org/challenges/imageclef-2019-caption-concept-detection-6812fec9-8c9e-40ad-9fb9-cc1721c94cc1).

Get started
-----------
To download the images, clone the repository and run

```bash
python scripts/fetch.py
```

Troubleshooting
---------------

If you see many download errors and/or you have a slow internet connection, try to reduce the number of processes to one:

```bash
python scripts/fetch.py -n 1
```

If on Windows, make sure `wget` is installed and its location (e.g. `C:\Program Files (x86)\GnuWin32\bin`) is added to the `Path` environment variable. Or install [Ubuntu on WSL](https://ubuntu.com/wsl).

Citation
--------
If you use this dataset for your own research, please cite the following paper:
> O. Pelka, S. Koitka, J. Rückert, F. Nensa, C.M. Friedrich,  
> ["__Radiology Objects in COntext (ROCO): A Multimodal Image Dataset__"](https://labels.tue-image.nl/wp-content/uploads/2018/09/AM-04.pdf).  
> MICCAI Workshop on Large-scale Annotation of Biomedical Data and Expert Label Synthesis (LABELS) 2018, September 16, 2018, Granada, Spain. Lecture Notes on Computer Science (LNCS), vol. 11043, pp. 180-189, Springer Cham, 2018.  
> doi: [10.1007/978-3-030-01364-6_20](https://doi.org/10.1007/978-3-030-01364-6_20)
