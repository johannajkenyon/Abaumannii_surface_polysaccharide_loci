<a href="[https://github.com/klebgenomics/Kaptive/](https://github.com/klebgenomics/Kaptive/)">
    <img align="right" src="https://github.com/klebgenomics/Kaptive/blob/master/docs/assets/logo.png?raw=true" alt="Kaptive" width="200">
</a>

# Decentralised _in silico_ serotyping databases
*A template repo for curating [Kaptive](https://github.com/klebgenomics/Kaptive/) databases*

[![Streamlit App](https://img.shields.io/badge/Streamlit-%23FE4B4B.svg?logo=streamlit&logoColor=white)](https://kaptive-database-validator.streamlit.app/)
[![Release Database](https://github.com/tomdstanton/kaptive-db-template/actions/workflows/release.yml/badge.svg)](https://github.com/tomdstanton/kaptive-db-template/actions/workflows/release.yml)

## How to use 👉
Just click the green "Use this template" button in the top-right corner, create your repo and upload your database Genbank files!

## Metadata 📀
All Kaptive databases now must be accompanied with a metadata [TOML file](https://toml.io/) with the **same name** as the corresponding Genbank file, 
with a '.toml' extension in place of the '.gbk' extension.

Below is an example of the _Klebsiella pneumoniae_ Species Complex K-locus database metadata:

```toml
name = "Klebsiella_pneumoniae_Species_Complex_K"
keyword = "kpsc_k"
genbank = "Klebsiella_pneumoniae_Species_Complex_K.gbk"
organism = "Klebsiella pneumoniae Species Complex"
taxon = 3390273
antigen = "Capsular polysaccharide"
pathway = "Wzx/Wzy-dependent"
prefix = "K"
version = "3.2.1"
id_threshold = 82.5
doi = ["TBD"]
owner = "klebgenomics"
repo = "KpSC_surface_antigen_loci"
branch = "main"
contact = { "Kelly Wyres" = "kaptive.typing@gmail.com" }

[phenotype_logic]
"Capsule null" = { loci = ["KL*"], inactive_genes = ['wza','wzb','wzc','wzx','wzy', 'wcaJ*', 'wbaP*'], priority = 100 }
"K37" = { loci = ["KL22"], inactive_genes = ["atr12"] }
```

### Phenotype Logic 🧠
The [TOML format](https://toml.io/) is a simple, human-readable, easily-parsable format, which makes it perfect for metadata. For these reasons, it also made sense to define the
phenotype logic here too! Whilst this is still a work-in-progress, here is how we're currently defining it:

1. Each line represents a unique phenotype that can be applied to a serotyping call.
1. All fields accept a wildcard ([`*`](https://docs.python.org/3/library/fnmatch.html)) for selecting multiple items.
1. Loci are defined by the "loci" field - here you can choose the specific loci the logic applies to.

### App 💫
We have created a simple [Streamlit app](https://kaptive-database-validator.streamlit.app/) to help you generate the metadata any database in your repo!

## Database Versioning & Release Workflow 🚀
This repository uses a fully automated Continuous Integration / Continuous Deployment (CI/CD) pipeline to manage database versions.

You do not need to manually edit version numbers or create Git tags. The pipeline relies on Semantic Versioning (SemVer) and reads your 
commit messages to automatically calculate the correct version bump, update the corresponding .toml files, and generate 
database-specific release tags.

### How It Works: Conventional Commits ⚙️
The automation script decides how to version a database based on the language used in your commit messages. 
We follow the [Conventional Commits standard](https://www.conventionalcommits.org/en/v1.0.0/).

When you commit changes to a database Genbank file, prefix your commit message with one of the following:

#### Patch Bump 🔨
`fix:` - Use this for correcting typos, fixing broken logic rules, or minor backwards-compatible bug fixes.

- Example: `fix: correct wcaJ truncation rule in Klebsiella`
- Result: `v3.2.1 ➡️ v3.2.2`

#### Minor Bump 🛠️
`feat:` - Use this when adding new features, such as adding a new locus, a new glycosidic linkage, or expanding the phenotype logic in a backwards-compatible way.

- Example: `feat: add KL102 locus to Klebsiella_pneumoniae_K`
- Result: `v3.2.1 ➡️ v3.3.0`

#### Major Bump 🧰
`feat!:` or `[major]` - Use this for breaking changes, such as overhauling the TOML schema, changing existing core 
nomenclature, or deleting previously supported loci.

- Example: `feat!: restructure TOML schema for phenotype logic`
- Result: `v3.2.1 ➡️ v4.0.0`

#### No Bump 🤷
`chore:`, `docs:`, `style:` - Changes to `README`s, generic repository maintenance, or formatting will not trigger a version bump.

### Day-to-Day Workflows 🖇️
#### Updating an Existing Database ⬆️
To update an existing database, simply make your changes to the .gbk files and commit them using the appropriate prefix.

```bash
# 1. Make changes to your files
git add Klebsiella_pneumoniae_K.gbk Klebsiella_pneumoniae_K.toml

# 2. Commit using a Conventional Commit message
git commit -m "feat: add new Wzy-dependent linkage rules"

# 3. Push to main
git push origin main
```

**What happens next?** The GitHub Action will detect the changes to the Klebsiella files, parse the `feat:` prefix, 
bump the minor version in `Klebsiella_pneumoniae_K.toml`, commit that TOML update back to the repository, 
and create a scoped tag (e.g., `Klebsiella_pneumoniae_K-v3.3.0`).

#### Adding a Completely New Database ➡️
The pipeline is database-agnostic. To add a new database, you just need to drop the required files into the repository.

1. Add your new GenBank file (e.g., `seudomonas_aeruginosa_O.gbk`).
2. Add a starting TOML file (e.g., `Pseudomonas_aeruginosa_O.toml`) and manually set the initial version (e.g., `version = "1.0.0"`).
3. Commit and push:

```bash
git add Pseudomonas_aeruginosa_O.*
git commit -m "feat: initial release of Pseudomonas O-locus database"
git push origin main
```

The pipeline will automatically discover the new `.toml` file, register the `feat:` bump (e.g., `v1.1.0`), and tag it.

#### Updating Multiple Databases at Once ⬆️⬆️
If you make a broad change that affects multiple databases (for example, fixing a shared logic rule across both Klebsiella_pneumoniae_K and Klebsiella_pneumoniae_O), simply commit them together:

```bash
git add *.logic
git commit -m "fix: standardize capsule null logic across all databases"
git push origin main**
```

The workflow will detect every database that was modified, bump their `.toml` versions independently, and generate a separate release tag for each one.

### Important Rules ⚠️
 - Never manually edit the version = "..." string in the .toml files. The Python automation (tomlkit) handles this to ensure
   strict alignment between the file contents and the Git tags.
 - Ensure file names match exactly. The base name of the TOML file must match the base name of the GenBank files
   (e.g., `Database_Name.toml` pairs with `Database_Name.gbk`).
 - Pull before you work. Because the GitHub Action makes automated commits to update the TOML files, always
   run `git pull` before starting new work to ensure your local branch has the latest version strings.

## References 📚
[^1]: Stanton TD, Hetland MAK, Löhr IH, Holt KE, Wyres KL. Fast and
    Accurate in silico Antigen Typing with Kaptive 3.
    2025 _Microbial Genomics_ 11(6):001428.
    <https://doi.org/10.1099/mgen.0.001428>
