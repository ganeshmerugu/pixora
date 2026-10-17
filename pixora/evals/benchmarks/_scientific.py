"""Golden benchmark data for scientific paper documents."""
from __future__ import annotations

from pixora.evals.benchmarks.schemas import SCIENTIFIC_SCHEMA


def get_scientific() -> list[dict]:
    return [
        # ── TYPICAL 1 ──────────────────────────────────────────────
        {
            "document_id": "bench_sci_001",
            "doc_type": "scientific_paper",
            "filename": "neural_nets_2024.pdf",
            "difficulty": "typical",
            "text": (
                "RESEARCH ARTICLE\n\n"
                "Title: Scalable Transformer Architectures for Low-Resource Language Modeling\n"
                "Authors: Wei Chen, Priya Patel, Marcus Johnson, Elena Sorokina\n"
                "Journal: Journal of Machine Learning Research\n"
                "Publication Date: 06/15/2024\n"
                "DOI: 10.1234/jmlr.2024.08.042\n\n"
                "Abstract: We propose a novel parameter-efficient transformer variant "
                "that achieves state-of-the-art performance on low-resource language "
                "benchmarks while reducing training compute by 40%. Our approach "
                "combines adapter layers with structured pruning to maintain model "
                "quality under constrained budgets.\n\n"
                "Keywords: transformers, low-resource NLP, parameter efficiency, pruning\n\n"
                "1. Introduction\n"
                "Large language models have demonstrated remarkable capabilities...\n\n"
                "6. Conclusion: Our results demonstrate that structured pruning combined "
                "with adapter layers provides a viable path toward deploying transformer "
                "models in resource-constrained settings without significant quality loss.\n"
            ),
            "expected": {
                "title": "Scalable Transformer Architectures for Low-Resource Language Modeling",
                "authors": "Wei Chen, Priya Patel, Marcus Johnson, Elena Sorokina",
                "journal": "Journal of Machine Learning Research",
                "publication_date": "06/15/2024",
                "doi": "10.1234/jmlr.2024.08.042",
                "abstract": (
                    "We propose a novel parameter-efficient transformer variant "
                    "that achieves state-of-the-art performance on low-resource language "
                    "benchmarks while reducing training compute by 40%. Our approach "
                    "combines adapter layers with structured pruning to maintain model "
                    "quality under constrained budgets."
                ),
                "keywords": "transformers, low-resource NLP, parameter efficiency, pruning",
                "conclusion": (
                    "Our results demonstrate that structured pruning combined "
                    "with adapter layers provides a viable path toward deploying transformer "
                    "models in resource-constrained settings without significant quality loss."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── TYPICAL 2 ──────────────────────────────────────────────
        {
            "document_id": "bench_sci_002",
            "doc_type": "scientific_paper",
            "filename": "crispr_gene_editing.pdf",
            "difficulty": "typical",
            "text": (
                "ORIGINAL RESEARCH\n\n"
                "Title: CRISPR-Cas9 Mediated Correction of Sickle Cell Mutations in Human Hematopoietic Stem Cells\n"
                "Authors: Sarah Okonkwo, James Liu, Fatima Al-Rashid\n"
                "Journal: Nature Biotechnology\n"
                "Publication Date: 03/22/2024\n"
                "DOI: 10.1038/nbt.2024.1147\n\n"
                "Abstract: We demonstrate efficient correction of the sickle cell "
                "disease-causing HBB E6V mutation in patient-derived CD34+ cells using "
                "an optimized CRISPR-Cas9 ribonucleoprotein delivery system. Edited "
                "cells showed 78% allele correction and maintained multilineage "
                "engraftment potential in xenograft models.\n\n"
                "Keywords: CRISPR, sickle cell disease, gene therapy, hematopoietic stem cells\n\n"
                "Conclusion: Our optimized RNP delivery protocol achieves therapeutically "
                "relevant correction rates in patient-derived HSCs, supporting advancement "
                "to first-in-human clinical trials.\n"
            ),
            "expected": {
                "title": "CRISPR-Cas9 Mediated Correction of Sickle Cell Mutations in Human Hematopoietic Stem Cells",
                "authors": "Sarah Okonkwo, James Liu, Fatima Al-Rashid",
                "journal": "Nature Biotechnology",
                "publication_date": "03/22/2024",
                "doi": "10.1038/nbt.2024.1147",
                "abstract": (
                    "We demonstrate efficient correction of the sickle cell "
                    "disease-causing HBB E6V mutation in patient-derived CD34+ cells using "
                    "an optimized CRISPR-Cas9 ribonucleoprotein delivery system. Edited "
                    "cells showed 78% allele correction and maintained multilineage "
                    "engraftment potential in xenograft models."
                ),
                "keywords": "CRISPR, sickle cell disease, gene therapy, hematopoietic stem cells",
                "conclusion": (
                    "Our optimized RNP delivery protocol achieves therapeutically "
                    "relevant correction rates in patient-derived HSCs, supporting advancement "
                    "to first-in-human clinical trials."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── TYPICAL 3 ──────────────────────────────────────────────
        {
            "document_id": "bench_sci_003",
            "doc_type": "scientific_paper",
            "filename": "quantum_entanglement.pdf",
            "difficulty": "typical",
            "text": (
                "Title: Observation of Long-Range Quantum Entanglement in Topological Superconductors\n"
                "Authors: Dmitri Volkov, Yuki Tanaka, Maria Gonzalez\n"
                "Journal: Physical Review Letters\n"
                "Publication Date: 11/08/2023\n"
                "DOI: 10.1103/PhysRevLett.131.206801\n\n"
                "Abstract: We report the first experimental observation of spatially "
                "separated Majorana zero modes exhibiting non-local quantum entanglement "
                "over distances exceeding 10 micrometers in a hybrid semiconductor-"
                "superconductor nanowire platform. Our results provide strong evidence "
                "for topological protection of quantum information.\n\n"
                "Keywords: Majorana fermions, topological superconductors, quantum entanglement\n\n"
                "Conclusion: The observed long-range entanglement signatures are consistent "
                "with theoretical predictions for topologically protected Majorana modes "
                "and represent a key milestone toward fault-tolerant topological quantum computing.\n"
            ),
            "expected": {
                "title": "Observation of Long-Range Quantum Entanglement in Topological Superconductors",
                "authors": "Dmitri Volkov, Yuki Tanaka, Maria Gonzalez",
                "journal": "Physical Review Letters",
                "publication_date": "11/08/2023",
                "doi": "10.1103/PhysRevLett.131.206801",
                "abstract": (
                    "We report the first experimental observation of spatially "
                    "separated Majorana zero modes exhibiting non-local quantum entanglement "
                    "over distances exceeding 10 micrometers in a hybrid semiconductor-"
                    "superconductor nanowire platform. Our results provide strong evidence "
                    "for topological protection of quantum information."
                ),
                "keywords": "Majorana fermions, topological superconductors, quantum entanglement",
                "conclusion": (
                    "The observed long-range entanglement signatures are consistent "
                    "with theoretical predictions for topologically protected Majorana modes "
                    "and represent a key milestone toward fault-tolerant topological quantum computing."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── TYPICAL 4 ──────────────────────────────────────────────
        {
            "document_id": "bench_sci_004",
            "doc_type": "scientific_paper",
            "filename": "catalysis_green_chem.pdf",
            "difficulty": "typical",
            "text": (
                "Title: Earth-Abundant Metal Catalysts for Selective CO2 Hydrogenation to Methanol\n"
                "Authors: Ananya Sharma, Robert Klein, Jie Wu\n"
                "Journal: ACS Catalysis\n"
                "Publication Date: 09/30/2024\n"
                "DOI: 10.1021/acscatal.2024.14892\n\n"
                "Abstract: We report a series of copper-zinc-alumina catalysts doped "
                "with trace manganese that achieve 92% selectivity for methanol at "
                "250 degrees Celsius and 50 bar CO2/H2 pressure. The catalysts maintain "
                "stable performance over 500 hours on stream.\n\n"
                "Keywords: CO2 hydrogenation, methanol synthesis, heterogeneous catalysis, green chemistry\n\n"
                "Conclusion: Manganese doping of CuZnAl catalysts provides a scalable and "
                "cost-effective route to selective CO2-to-methanol conversion under "
                "industrially relevant conditions.\n"
            ),
            "expected": {
                "title": "Earth-Abundant Metal Catalysts for Selective CO2 Hydrogenation to Methanol",
                "authors": "Ananya Sharma, Robert Klein, Jie Wu",
                "journal": "ACS Catalysis",
                "publication_date": "09/30/2024",
                "doi": "10.1021/acscatal.2024.14892",
                "abstract": (
                    "We report a series of copper-zinc-alumina catalysts doped "
                    "with trace manganese that achieve 92% selectivity for methanol at "
                    "250 degrees Celsius and 50 bar CO2/H2 pressure. The catalysts maintain "
                    "stable performance over 500 hours on stream."
                ),
                "keywords": "CO2 hydrogenation, methanol synthesis, heterogeneous catalysis, green chemistry",
                "conclusion": (
                    "Manganese doping of CuZnAl catalysts provides a scalable and "
                    "cost-effective route to selective CO2-to-methanol conversion under "
                    "industrially relevant conditions."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── TYPICAL 5 ──────────────────────────────────────────────
        {
            "document_id": "bench_sci_005",
            "doc_type": "scientific_paper",
            "filename": "behavioral_economics.pdf",
            "difficulty": "typical",
            "text": (
                "Title: Nudge Fatigue and Decision Quality in Repeated Consumer Choices\n"
                "Authors: Clara Nilsson, David Osei, Kenji Watanabe\n"
                "Journal: American Economic Review\n"
                "Publication Date: 01/15/2024\n"
                "DOI: 10.1257/aer.2024.114.0238\n\n"
                "Abstract: Using a pre-registered field experiment with 12,000 "
                "participants across three online retail platforms, we show that "
                "repeated exposure to choice-architecture nudges leads to a 34% "
                "decline in nudge effectiveness after 60 days. We term this phenomenon "
                "nudge fatigue and propose a rotation framework to sustain impact.\n\n"
                "Keywords: behavioral economics, nudges, choice architecture, field experiment\n\n"
                "Conclusion: Our findings suggest that policymakers and firms should adopt "
                "dynamic nudge rotation strategies rather than static default interventions "
                "to maintain long-term behavioral impact.\n"
            ),
            "expected": {
                "title": "Nudge Fatigue and Decision Quality in Repeated Consumer Choices",
                "authors": "Clara Nilsson, David Osei, Kenji Watanabe",
                "journal": "American Economic Review",
                "publication_date": "01/15/2024",
                "doi": "10.1257/aer.2024.114.0238",
                "abstract": (
                    "Using a pre-registered field experiment with 12,000 "
                    "participants across three online retail platforms, we show that "
                    "repeated exposure to choice-architecture nudges leads to a 34% "
                    "decline in nudge effectiveness after 60 days. We term this phenomenon "
                    "nudge fatigue and propose a rotation framework to sustain impact."
                ),
                "keywords": "behavioral economics, nudges, choice architecture, field experiment",
                "conclusion": (
                    "Our findings suggest that policymakers and firms should adopt "
                    "dynamic nudge rotation strategies rather than static default interventions "
                    "to maintain long-term behavioral impact."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── EDGE 1 ─────────────────────────────────────────────────
        {
            "document_id": "bench_sci_006",
            "doc_type": "scientific_paper",
            "filename": "large_collab_physics.pdf",
            "difficulty": "edge",
            "text": (
                "Title: Search for Supersymmetric Partners of the Top Quark at 13.6 TeV\n"
                "Authors: A. Aad, B. Abbott, K. Abdallah, S. Abdel Khalek, O. Abdinov, "
                "R. Aben, B. Abi, M. Abolins, O. AbouZeid, H. Abramowicz, "
                "D. Acosta, L. Adamczyk, J. Adelman, S. Adomeit, T. Adye, "
                "A. Agatonovic-Jovin, J. Agnew, P. Agustoni, S. Ahmad, F. Ahmadov, "
                "G. Aielli, H. Akerstedt, T. Akesson, A. Akimov\n"
                "Journal: Physical Review D\n"
                "Publication Date: 08/01/2024\n"
                "DOI: 10.1103/PhysRevD.109.052004\n\n"
                "Abstract: We present a search for direct pair production of top squarks "
                "using 140 fb-1 of proton-proton collision data collected by the ATLAS "
                "detector. No significant excess above the Standard Model prediction is "
                "observed and exclusion limits are set.\n\n"
                "Keywords: supersymmetry, LHC, top squark, ATLAS\n\n"
                "Conclusion: Top squark masses below 1.25 TeV are excluded at 95% "
                "confidence level for massless neutralinos.\n"
            ),
            "expected": {
                "title": "Search for Supersymmetric Partners of the Top Quark at 13.6 TeV",
                "authors": (
                    "A. Aad, B. Abbott, K. Abdallah, S. Abdel Khalek, O. Abdinov, "
                    "R. Aben, B. Abi, M. Abolins, O. AbouZeid, H. Abramowicz, "
                    "D. Acosta, L. Adamczyk, J. Adelman, S. Adomeit, T. Adye, "
                    "A. Agatonovic-Jovin, J. Agnew, P. Agustoni, S. Ahmad, F. Ahmadov, "
                    "G. Aielli, H. Akerstedt, T. Akesson, A. Akimov"
                ),
                "journal": "Physical Review D",
                "publication_date": "08/01/2024",
                "doi": "10.1103/PhysRevD.109.052004",
                "abstract": (
                    "We present a search for direct pair production of top squarks "
                    "using 140 fb-1 of proton-proton collision data collected by the ATLAS "
                    "detector. No significant excess above the Standard Model prediction is "
                    "observed and exclusion limits are set."
                ),
                "keywords": "supersymmetry, LHC, top squark, ATLAS",
                "conclusion": (
                    "Top squark masses below 1.25 TeV are excluded at 95% "
                    "confidence level for massless neutralinos."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── EDGE 2 ─────────────────────────────────────────────────
        {
            "document_id": "bench_sci_007",
            "doc_type": "scientific_paper",
            "filename": "special_chars_title.pdf",
            "difficulty": "edge",
            "text": (
                "Title: α-Synuclein Aggregation in Parkinson’s Disease: A β-Sheet → Amyloid Fibril Pathway\n"
                "Authors: Hans Müller, Émilie Dubé, José García-López\n"
                "Journal: Proceedings of the National Academy of Sciences\n"
                "Publication Date: 05/10/2024\n"
                "DOI: 10.1073/pnas.2024.121.e2318940\n\n"
                "Abstract: Using cryo-electron microscopy at 2.8 Å resolution, we "
                "resolve the structural transition from α-helical monomers to β-sheet-rich "
                "oligomers and ultimately mature amyloid fibrils of α-synuclein. We "
                "identify a druggable intermediate conformation.\n\n"
                "Keywords: α-synuclein, Parkinson’s disease, amyloid, cryo-EM\n\n"
                "Conclusion: The identified oligomeric intermediate represents a "
                "promising therapeutic target for disease-modifying interventions.\n"
            ),
            "expected": {
                "title": "α-Synuclein Aggregation in Parkinson’s Disease: A β-Sheet → Amyloid Fibril Pathway",
                "authors": "Hans Müller, Émilie Dubé, José García-López",
                "journal": "Proceedings of the National Academy of Sciences",
                "publication_date": "05/10/2024",
                "doi": "10.1073/pnas.2024.121.e2318940",
                "abstract": (
                    "Using cryo-electron microscopy at 2.8 Å resolution, we "
                    "resolve the structural transition from α-helical monomers to β-sheet-rich "
                    "oligomers and ultimately mature amyloid fibrils of α-synuclein. We "
                    "identify a druggable intermediate conformation."
                ),
                "keywords": "α-synuclein, Parkinson’s disease, amyloid, cryo-EM",
                "conclusion": (
                    "The identified oligomeric intermediate represents a "
                    "promising therapeutic target for disease-modifying interventions."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── EDGE 3 ─────────────────────────────────────────────────
        {
            "document_id": "bench_sci_008",
            "doc_type": "scientific_paper",
            "filename": "preprint_no_doi.pdf",
            "difficulty": "edge",
            "text": (
                "PREPRINT — NOT PEER REVIEWED\n\n"
                "Title: Self-Supervised Representation Learning for Satellite Imagery Change Detection\n"
                "Authors: Lakshmi Iyer, Thomas Bergmann\n"
                "Journal: arXiv preprint\n"
                "Publication Date: 2024-02-28\n\n"
                "Abstract: We introduce SatCLR, a contrastive learning framework for "
                "multi-temporal satellite imagery that requires no labeled data. "
                "SatCLR outperforms supervised baselines on three change detection "
                "benchmarks by an average of 6.3 mAP points.\n\n"
                "Keywords: remote sensing, self-supervised learning, change detection, satellite imagery\n\n"
                "Conclusion: Self-supervised pre-training on unlabeled satellite archives "
                "is a practical and effective alternative to costly manual annotation for "
                "change detection tasks.\n"
            ),
            "expected": {
                "title": "Self-Supervised Representation Learning for Satellite Imagery Change Detection",
                "authors": "Lakshmi Iyer, Thomas Bergmann",
                "journal": "arXiv preprint",
                "publication_date": "2024-02-28",
                "doi": None,
                "abstract": (
                    "We introduce SatCLR, a contrastive learning framework for "
                    "multi-temporal satellite imagery that requires no labeled data. "
                    "SatCLR outperforms supervised baselines on three change detection "
                    "benchmarks by an average of 6.3 mAP points."
                ),
                "keywords": "remote sensing, self-supervised learning, change detection, satellite imagery",
                "conclusion": (
                    "Self-supervised pre-training on unlabeled satellite archives "
                    "is a practical and effective alternative to costly manual annotation for "
                    "change detection tasks."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── ADVERSARIAL 1 ──────────────────────────────────────────
        {
            "document_id": "bench_sci_009",
            "doc_type": "scientific_paper",
            "filename": "garbled_doi.pdf",
            "difficulty": "adversarial",
            "text": (
                "Title: Meta-Analysis of Cognitive Behavioral Therapy Outcomes for Generalized Anxiety\n"
                "Authors: Rachel Green, Rachel Green, David Kim, Sofia Petrov\n"
                "Journal: The Lancet Psychiatry\n"
                "Publication Date: 07/01/2024\n"
                "DOI: I0.I0I6/S22I5-0366(24)OOI82-7\n\n"
                "Abstract: This systematic review and meta-analysis of 84 randomized "
                "controlled trials comprising 9,247 participants finds that CBT produces "
                "a large effect size (Hedges g = 0.82) for generalized anxiety disorder "
                "symptoms at post-treatment.\n\n"
                "Keywords: CBT, anxiety, meta-analysis, RCT\n\n"
                "Conclusion: CBT remains the most empirically supported psychotherapy "
                "for generalized anxiety disorder across age groups and delivery formats.\n"
            ),
            "expected": {
                "title": "Meta-Analysis of Cognitive Behavioral Therapy Outcomes for Generalized Anxiety",
                "authors": "Rachel Green, Rachel Green, David Kim, Sofia Petrov",
                "journal": "The Lancet Psychiatry",
                "publication_date": "07/01/2024",
                "doi": "I0.I0I6/S22I5-0366(24)OOI82-7",
                "abstract": (
                    "This systematic review and meta-analysis of 84 randomized "
                    "controlled trials comprising 9,247 participants finds that CBT produces "
                    "a large effect size (Hedges g = 0.82) for generalized anxiety disorder "
                    "symptoms at post-treatment."
                ),
                "keywords": "CBT, anxiety, meta-analysis, RCT",
                "conclusion": (
                    "CBT remains the most empirically supported psychotherapy "
                    "for generalized anxiety disorder across age groups and delivery formats."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
        # ── ADVERSARIAL 2 ──────────────────────────────────────────
        {
            "document_id": "bench_sci_010",
            "doc_type": "scientific_paper",
            "filename": "contradictory_dates.pdf",
            "difficulty": "adversarial",
            "text": (
                "Title: Deep Reinforcement Learning for Autonomous Drone Navigation in Urban Environments\n"
                "Authors: Omar Hassan, Lisa Wang\n"
                "Journal: IEEE Transactions on Robotics\n"
                "Publication Date: 13/45/2024\n"
                "DOI: 10.1109/TRO.2024.3389201\n\n"
                "Received: March 2025 | Accepted: January 2024 | Published: 13/45/2024\n\n"
                "Abstract: We present a sim-to-real deep reinforcement learning pipeline "
                "that enables autonomous quadrotor navigation through dense urban "
                "environments with dynamic obstacles. Our policy achieves a 96.7% "
                "collision-free navigation rate in real-world tests.\n\n"
                "Keywords: reinforcement learning, UAV, autonomous navigation, sim-to-real\n\n"
                "Conclusion: The proposed sim-to-real transfer framework significantly "
                "reduces the reality gap for urban drone navigation tasks.\n"
            ),
            "expected": {
                "title": "Deep Reinforcement Learning for Autonomous Drone Navigation in Urban Environments",
                "authors": "Omar Hassan, Lisa Wang",
                "journal": "IEEE Transactions on Robotics",
                "publication_date": "13/45/2024",
                "doi": "10.1109/TRO.2024.3389201",
                "abstract": (
                    "We present a sim-to-real deep reinforcement learning pipeline "
                    "that enables autonomous quadrotor navigation through dense urban "
                    "environments with dynamic obstacles. Our policy achieves a 96.7% "
                    "collision-free navigation rate in real-world tests."
                ),
                "keywords": "reinforcement learning, UAV, autonomous navigation, sim-to-real",
                "conclusion": (
                    "The proposed sim-to-real transfer framework significantly "
                    "reduces the reality gap for urban drone navigation tasks."
                ),
            },
            "schema_nodes": SCIENTIFIC_SCHEMA,
        },
    ]
