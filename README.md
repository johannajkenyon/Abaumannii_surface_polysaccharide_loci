<img align="right" src="https://github.com/klebgenomics/Kaptive/blob/master/docs/assets/logo.png?raw=true" alt="Kaptive" width="200">

# _A. baumannii_ Surface Antigen Loci
*[Kaptive](https://github.com/klebgenomics/Kaptive/) databases for Acinetobacter baumannii*

[![Streamlit App](https://img.shields.io/badge/Streamlit-%23FE4B4B.svg?logo=streamlit&logoColor=white)](https://kaptive-database-validator.streamlit.app/)
[![Release Database](https://github.com/tomdstanton/A_baumannii_Surface_Antigen_Loci/actions/workflows/release.yml/badge.svg)](https://github.com/tomdstanton/A_baumannii_Surface_Antigen_Loci/actions/workflows/release.yml)

## *Acinetobacter baunannii* K and OC locus databases

The *A. baumannii* K (capsule) locus reference database
(`Acinetobacter_baumannii_K.gbk`)
contains annotated sequences for 241 distinct K loci.

The *A. baumannii* OC (lipooligosaccharide outer core) locus reference
database
(`Acinetobacter_baumannii_OC.gbk`)
contains annotated sequences for 22 distinct OC loci.

!!! warning
    These databases have been developed and tested specifically for *A.
    baumannii* and may not be suitable for screening other *Acinetobacter*
    species. You can check that your assembly is a true *A. baumannii* by
    screening for the *oxaAB* gene e.g. using blastn.

### Database versions:

- Kaptive v0.7.0 and above include the original *A. baumannii* K and OC
  locus databases, as described in [Wyres, KL. et al. Microbial Genomics
  2020](https://doi.org/10.1099/mgen.0.000339).
- Kaptive v2.0.1 and above include 149 novel primary *A. baumannii* K
  locus references as described in Cahill, S.M. et al. 2022. An update
  to the database for *Acinetobacter baumannii* capsular polysaccharide
  locus typing extends the extensive and diverse repertoire of genes
  found at and outside the K locus. [Microbial
  Genomics](https://doi.org/10.1099/mgen.0.000878).
- Kaptive v2.0.2 and above include special logic parameters that enable
  prediction of the capsule polysaccharide type based on KL or the
  detected combination of a specific KL with 'extra genes' elsewhere in
  the chromosome as indicated in the table below and described in
  Cahill, S.M. et al. 2022. An update to the database for *A. baumannii*
  capsular polysaccharide locus typing extends the extensive and diverse
  repertoire of genes found at and outside the K locus. [Microbial
  Genomics](https://doi.org/10.1099/mgen.0.000878).
- Kaptive v2.0.5 and above includes a further 10 *A. baumannii* OC locus
  references (OCL13-OCL22) as described in Sorbello, B. et al.
  Identification of further variation at the lipooligosaccharide outer
  core locus in *Acinetobacter baumannii* genomes and extension of the
  OCL reference sequence database for Kaptive. [Microbial Genomics](https://doi.org/10.1099/mgen.0.001042).


## References 📚
[^1]: Stanton TD, Hetland MAK, Löhr IH, Holt KE, Wyres KL. Fast and
    Accurate in silico Antigen Typing with Kaptive 3.
    2025 _Microbial Genomics_ 11(6):001428.
    <https://doi.org/10.1099/mgen.0.001428>
