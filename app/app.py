import streamlit as st
import toml
import urllib.request
import urllib.parse
import json
import semver
import io
import base64
import fnmatch
from re import compile as re_compile
from gb_io import iter as GenbankIterator

st.set_page_config(page_title="Kaptive Database Validator", layout="centered")

# --- Header with Right-Aligned Logo ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("Kaptive Database Validator")
    st.markdown("""
    Fill out the fields below to validate your [Kaptive](https://github.com/klebgenomics/Kaptive) database and generate the metadata file.
    Note that you will need a [Github account](https://github.com/signup) to host your database.
    """)
with header_col2:
    st.image("https://github.com/klebgenomics/Kaptive/blob/master/docs/assets/logo.png?raw=true", width=120)

# Initialize persistent storage for DOIs, Contacts, and Phenotypes
if 'doi_list' not in st.session_state:
    st.session_state.doi_list = []
    
if 'contact_dict' not in st.session_state:
    st.session_state.contact_dict = {}

if 'phenotype_dict' not in st.session_state:
    st.session_state.phenotype_dict = {}

# Helper Function: Wildcard Matcher
def get_matches(pattern_str, options):
    patterns = [p.strip() for p in pattern_str.split(',') if p.strip()]
    matched = set()
    for p in patterns:
        matched.update(fnmatch.filter(options, p))
    return sorted(list(matched))

def parse_database(fh):
    _LOCUS_REGEX = re_compile(r'locus:\s?(.*)$')
    _SEROTYPE_REGEX = re_compile(r'type:\s?(.*)$')
    _EXTRA_REGEX = re_compile(r'Extra genes:\s?(.*)$')
    
    loci, genes, extra_genes = dict(), set(), set()
    for rec in GenbankIterator(fh):
        if not (notes := [i.value for i in rec.features[0].qualifiers if i.key == 'note']):
            raise ValueError(f'Locus has no "note" qualifiers: {rec.name}')

        locus_names, serotypes, extra_locus = [], [], False
        for note in notes:  # type: str
            if match := _EXTRA_REGEX.search(note):
                extra_locus = True
                break

            if match := _LOCUS_REGEX.search(note):
                locus_names.append(match.group(1))

            if match := _SEROTYPE_REGEX.search(note):
                serotypes.append(match.group(1))

        if not extra_locus:
            if not locus_names:
                raise ValueError(f'Locus has no valid "locus" qualifiers: {rec.name}')
            if len(locus_names) > 1:
                raise ValueError(f'Locus has multiple "locus" qualifiers: {rec.name}')

            locus = locus_names[0]
            serotype = serotypes[0] if serotypes else "Unknown"
            
            if locus in loci:
                raise ValueError(f'Database has multiple records for {locus}')
            
            loci[locus] = serotype

        gene_set = extra_genes if extra_locus else genes
        for feat in rec.features[1:]:
            if feat.kind == 'CDS':
                for i in feat.qualifiers:
                    if i.key == 'gene':
                        gene_set.add(i.value)

    return loci, genes, extra_genes


# Helper Function: Fetch DOIs from Crossref based on title search
@st.cache_data(ttl=3600)
def fetch_crossref_dois(search_term):
    if not search_term.strip():
        return []
    try:
        encoded_term = urllib.parse.quote(search_term)
        url = f"https://api.crossref.org/works?query.title={encoded_term}&select=title,DOI&rows=5"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Kaptive-Metadata-Generator/1.0 (mailto:kaptive.typing@gmail.com)'
        })
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        items = data.get("message", {}).get("items", [])
        results = []
        for item in items:
            title = item.get("title", ["Unknown Title"])[0]
            doi = item.get("DOI", "No DOI")
            if doi != "No DOI":
                results.append({"title": title, "doi": doi})
        return results
    except Exception:
        return []

# Helper Function: Fetch TaxIDs from NCBI Datasets API
@st.cache_data(ttl=3600) 
def fetch_ncbi_taxids(search_term):
    if not search_term.strip():
        return []
    try:
        encoded_term = urllib.parse.quote(search_term)
        url = f"https://api.ncbi.nlm.nih.gov/datasets/v2alpha/taxonomy/taxon_suggest/{encoded_term}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Kaptive-Metadata-Generator/1.0'})

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))

        results = []
        if "sci_name_and_ids" in data:
            for item in data["sci_name_and_ids"]:
                tax_id = item.get("tax_id")
                sci_name = item.get("sci_name")
                rank = item.get("rank", "Unknown").title()  
                label = f"{sci_name} ({rank}) [TaxID: {tax_id}]"
                results.append({
                    "label": label,
                    "id": int(tax_id),
                    "name": sci_name
                })
        return results
    except Exception as e:
        return []

@st.cache_data(ttl=300)
def fetch_github_repos(owner):
    if not owner.strip():
        return []
    try:
        url = f"https://api.github.com/users/{urllib.parse.quote(owner)}/repos?per_page=100&sort=updated"
        req = urllib.request.Request(url, headers={'User-Agent': 'Kaptive-Metadata-Generator/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        return [repo['name'] for repo in data]
    except Exception:
        return []

@st.cache_data(ttl=300)
def fetch_github_branches(owner, repo):
    if not owner.strip() or not repo.strip():
        return []
    try:
        url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/branches?per_page=100"
        req = urllib.request.Request(url, headers={'User-Agent': 'Kaptive-Metadata-Generator/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        return [branch['name'] for branch in data]
    except Exception:
        return []

@st.cache_data(ttl=300)
def fetch_github_gbk_files(owner, repo, branch):
    if not owner or not repo or not branch:
        return None
    try:
        url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/git/trees/{urllib.parse.quote(branch)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Kaptive-Metadata-Generator/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        return [item['path'] for item in data.get('tree', []) if item['path'].endswith('.gbk')]
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None

@st.cache_data(show_spinner=False, ttl=300)
def fetch_and_validate_genbank(owner, repo, branch, filename):
    if not filename:
        return None, None, None, "No file provided."
    try:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{urllib.parse.quote(filename)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Kaptive-Metadata-Generator/1.0'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()
            
        fh = io.BytesIO(raw_data)
        loci, genes, extra_genes = parse_database(fh)
        return loci, genes, extra_genes, None
    except Exception as e:
        return None, None, None, str(e)

def push_to_github(owner, repo, branch, filepath, content, token, commit_message):
    api_base = f"https://api.github.com/repos/{owner}/{repo}/contents/{urllib.parse.quote(filepath)}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Kaptive-Database-Validator/1.0"
    }

    sha = None
    get_url = f"{api_base}?ref={branch}"
    try:
        req = urllib.request.Request(get_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            sha = data.get('sha')
    except urllib.error.HTTPError as e:
        if e.code != 404:  
            return False, f"Error checking existing file: {e.reason}"

    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha

    try:
        req = urllib.request.Request(
            api_base, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers, 
            method='PUT'
        )
        with urllib.request.urlopen(req) as response:
            if response.status in [200, 201]:
                return True, "Successfully pushed to repository!"
            else:
                return False, f"Unexpected status code: {response.status}"
    except urllib.error.HTTPError as e:
        error_msg = json.loads(e.read().decode('utf-8')).get('message', e.reason)
        return False, f"Failed to push: {error_msg}"
    except Exception as e:
        return False, f"An error occurred: {str(e)}"


# --- Main UI Blocks ---
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Database 💽")
    owner = st.text_input("Owner 🆔", help='GitHub username or organisation where the database repo is hosted.')

    repos, repo, branches, branch, gbk_files, genbank = [], "", [], "", [], ""
    
    if owner:
        repos = fetch_github_repos(owner)
        if repos:
            default_index = 0
            repo = st.selectbox("Repo 📂", options=repos, index=default_index)
        else:
            st.warning("⚠️ Could not fetch repositories. Please enter manually.")
            repo = st.text_input("Repo 📂")

        if repo:
            branches = fetch_github_branches(owner, repo)
            if branches:
                default_branch_index = 0
                if "main" in branches:
                    default_branch_index = branches.index("main")
                elif "master" in branches:
                    default_branch_index = branches.index("master")
                    
                branch = st.selectbox("Branch 🪾", options=branches, index=default_branch_index)
            else:
                st.warning("⚠️ Could not fetch branches. Please enter manually.")
                branch = st.text_input("Branch 🪾", value="main")

            if branch:
                gbk_files = fetch_github_gbk_files(owner, repo, branch)
                if gbk_files is None:
                    st.error("⚠️ Repository or branch not found.")
                    genbank = st.text_input("GenBank File (Manual Entry)")
                elif len(gbk_files) == 0:
                    st.warning(f"No '.gbk' files found in {owner}/{repo} on branch '{branch}'.")
                    genbank = st.text_input("GenBank File (Manual Entry) 🗂️")
                else:
                    st.success(f"Found {len(gbk_files)} GenBank file(s)!")
                    genbank = st.selectbox("Select GenBank File 🗂️", options=gbk_files)
    else:
        st.info("👆 Please enter a GitHub username to load repositories.")

    default_org_name = ""
    if genbank and genbank.endswith('.gbk'):
        filename_only = genbank.split('/')[-1]
        filename_no_ext = filename_only.replace('.gbk', '')
        name_parts = filename_no_ext.split('_')
        
        if len(name_parts) >= 2:
            default_org_name = f"{name_parts[0]} {name_parts[1]}"
        elif len(name_parts) == 1:
            default_org_name = name_parts[0]

    organism_input = st.text_input("Search Organism Name 🧫", value=default_org_name, 
                                   help='This is automatically populated by the database name but can be overridden.')
    
    taxon = 0
    organism = ""
    
    if organism_input:
        ncbi_options = fetch_ncbi_taxids(organism_input)
        
        if ncbi_options:
            selected_option = st.selectbox(
                "Select NCBI Taxonomy Match 🌳",
                options=ncbi_options,
                format_func=lambda x: x["label"]
            )
            taxon = selected_option["id"]
            organism = selected_option["name"] 
            st.success(f"Selected Taxon ID: {taxon}")
        else:
            st.warning("No official NCBI records found. Please enter manually:")
            organism = st.text_input("Organism Custom Name", value=organism_input)
            taxon = st.number_input("Taxon ID (Manual)", value=571, step=1)
    else:
        st.info("👆 Enter an organism name to search the [NCBI taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy).")


with col2:
    st.subheader("Biology 🦠")
    prefix = st.text_input("Prefix", help='This refers to the antigen designation, such as "K" for the K-antigen.').upper()

    keyword = ""
    name = ""

    if prefix and organism:
        org_parts = organism.strip().split()
        genus_part = org_parts[0] if len(org_parts) > 0 else ""
        species_part = org_parts[1] if len(org_parts) > 1 else ""

        genus_letter = genus_part[0].lower() if genus_part else ""
        species_letters = species_part[:3].lower() if species_part else ""
        clean_prefix = prefix.lower().strip()

        suggested_keyword = f"{genus_letter}{species_letters}_{clean_prefix}"
        suggested_name = f"{organism.replace(' ', '_')}_{prefix}"

        keyword = st.text_input("Database Keyword 🔑", value=suggested_keyword, help='This will be used as the database CLI argument.')
        name = st.text_input("Database Name 📋", value=suggested_name, help='This will be used to refer to the database in tabular reports.')
    else:
        if not organism:
            st.info("👆 Please select an organism in the Database column to generate naming suggestions.")
        else:
            st.info("👆 Please enter an antigen prefix to generate naming suggestions.")

    id_threshold = st.slider(
        "Identity Threshold (%)", 
        min_value=0.0, max_value=100.0, value=82.5, step=0.5, format="%.1f",
        help="This referes to the pairwiswe amino-acid itdentity cutoff to determine whether two genes are homologs."
    )
    
    antigen = st.selectbox("Antigen 💉", ["Capsular polysaccharide", "Outer-core-lipopolysaccharide", "Other"],
                          help='The molecular name of the antigen.')
    if antigen == "Other":
        antigen = st.text_input("Specify Antigen")

    pathway = st.selectbox("Pathway 🧪", ["Wzx/Wzy-dependent", "ABC transporter", "Synthase-dependent", "Other"],
                          help='The biosynthetic pathway that produces the antigen.')
    if pathway == "Other":
        pathway = st.text_input("Specify Pathway")


with col3:
    st.subheader("Curation 📚")
    version_input = st.text_input("Version", value="0.0.0", help='This must adhere to [Semantic Versioning](https://semver.org/).')

    is_valid_version = True
    if not semver.VersionInfo.is_valid(version_input):
        st.error("⚠️ Invalid SemVer format. Must be MAJOR.MINOR.PATCH (e.g., '0.0.0').")
        is_valid_version = False

    version = version_input 
    
    st.markdown("**Curators / Contacts 🧑‍🔬**")
    
    if st.session_state.contact_dict:
        for c_name, c_email in list(st.session_state.contact_dict.items()):
            c1, c2 = st.columns([5, 1])
            c1.code(f"{c_name} <{c_email}>")
            if c2.button("❌", key=f"remove_contact_{c_name}"):
                del st.session_state.contact_dict[c_name]
                st.rerun()
    else:
        st.warning("⚠️ No curators listed. Dictionary will default to 'TBD'.")

    with st.expander("➕ Add Curator"):
        new_c_name = st.text_input("Name (e.g. John Doe)")
        new_c_email = st.text_input("Email (e.g. j.doe@email.com)")
        if st.button("Add to Curators"):
            if new_c_name and new_c_email:
                st.session_state.contact_dict[new_c_name.strip()] = new_c_email.strip()
                st.rerun()
            else:
                st.error("Both a name and email are required.")

    st.markdown("---")
    st.markdown("**Paper DOIs 📄**")
    
    search_query = st.text_input("Search Paper by Title ([Crossref](https://www.crossref.org/))")
    if search_query:
        api_results = fetch_crossref_dois(search_query)
        
        if api_results:
            selected_paper = st.selectbox(
                "Select matching paper:", 
                options=api_results, 
                format_func=lambda x: f"{x['title']} (DOI: {x['doi']})"
            )
            
            if st.button("➕ Add to Database DOIs"):
                if selected_paper['doi'] not in st.session_state.doi_list:
                    st.session_state.doi_list.append(selected_paper['doi'])
                    st.rerun() 
                else:
                    st.warning("This DOI is already in your list.")
        else:
            st.warning("No papers found on Crossref.")

    with st.expander("Manually add a DOI (if not on Crossref)"):
        manual_doi = st.text_input("Enter exact DOI:")
        if st.button("➕ Add Manual DOI") and manual_doi:
            if manual_doi not in st.session_state.doi_list:
                st.session_state.doi_list.append(manual_doi)
                st.rerun()

    if st.session_state.doi_list:
        for i, current_doi in enumerate(st.session_state.doi_list):
            c1, c2 = st.columns([5, 1])
            c1.code(current_doi)
            if c2.button("❌", key=f"remove_doi_{i}"):
                st.session_state.doi_list.pop(i)
                st.rerun()
    else:
        st.info("No DOIs added. Array will default to ['TBD'].")

# --- Database Validation Section ---
st.divider()
st.subheader("Database Validation ✅")

is_db_valid = False
loci, genes, extra_genes = {}, set(), set() # Define globally for the logic block downstream

if genbank:
    with st.spinner("Fetching and validating GenBank file from GitHub..."):
        res_loci, res_genes, res_extra, err = fetch_and_validate_genbank(owner, repo, branch, genbank)
        
        if err:
            st.error(f"⚠️ **Validation Failed:** {err}")
        else:
            is_db_valid = True
            loci, genes, extra_genes = res_loci, res_genes, res_extra
            st.success(f"Database valid! Successfully parsed **{len(loci)}** loci, **{len(genes)}** genes, and **{len(extra_genes)}** extra genes.")
            
            val_col1, val_col2, val_col3 = st.columns(3)
            with val_col1:
                with st.expander("View Loci Details"):
                    if loci:
                        st.write(loci)
                    else:
                        st.info("No loci found.")
            with val_col2:
                with st.expander("View Genes Details"):
                    if genes:
                        st.write(sorted(list(genes)))
                    else:
                        st.info("No genes found.")
            with val_col3:
                with st.expander("View Extra Genes Details"):
                    if extra_genes:
                        st.write(sorted(list(extra_genes)))
                    else:
                        st.info("No extra genes found.")
else:
    st.info("Select or enter a GenBank file above to validate.")


# --- Phenotype Logic Section ---
st.divider()
st.subheader("Phenotype Logic 🧬🧮")
st.markdown("Define complex phenotypic application rules based on loci match patterns and specific gene presence or absence. Wildcards (`*`) are supported.")

if st.session_state.phenotype_dict:
    for p_name, p_logic in list(st.session_state.phenotype_dict.items()):
        c1, c2 = st.columns([9, 1])
        
        logic_parts = [f"Loci: `{p_logic.get('loci', [])}`"]
        if 'inactive_genes' in p_logic:
            logic_parts.append(f"Inactive: `{p_logic['inactive_genes']}`")
        if 'extra_genes' in p_logic:
            logic_parts.append(f"Extra: `{p_logic['extra_genes']}`")
        if 'priority' in p_logic:
            logic_parts.append(f"Priority: `{p_logic['priority']}`")
            
        c1.info(f"**{p_name}** ➔ {' | '.join(logic_parts)}")
        
        if c2.button("❌", key=f"remove_pheno_{p_name}"):
            del st.session_state.phenotype_dict[p_name]
            st.rerun()
else:
    st.info("No phenotype logic defined. (Optional)")

with st.expander("➕ Add Phenotype Logic", expanded=True):
    p_name = st.text_input("Phenotype Name (e.g., 'Capsule null', 'O2β')")
    
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        p_loci = st.text_input("Loci", help="Comma-separated list (e.g., 'KL*', 'OL2α*'). Applies to these base loci.")
        # Real-time Wildcard Preview
        if is_db_valid and p_loci:
            m_loci = get_matches(p_loci, loci.keys())
            st.caption(f"**Matches ({len(m_loci)}):** {', '.join(m_loci) if m_loci else 'None'}")
            
        p_priority = st.number_input("Priority", value=50, step=1, help="Order of logic application. Higher/lower numbers determine precedence. Default is 50.")
        
    with p_col2:
        p_inactive = st.text_input("Inactive Genes", help="Comma-separated list. Phenotype applied if ANY of these genes are inactivated.")
        # Real-time Wildcard Preview
        if is_db_valid and p_inactive:
            m_inactive = get_matches(p_inactive, genes)
            st.caption(f"**Matches ({len(m_inactive)}):** {', '.join(m_inactive) if m_inactive else 'None'}")
            
        p_extra = st.text_input("Extra Genes", help="Comma-separated list. Phenotype applied if ALL of these genes are present.")
        # Real-time Wildcard Preview
        if is_db_valid and p_extra:
            m_extra = get_matches(p_extra, extra_genes)
            st.caption(f"**Matches ({len(m_extra)}):** {', '.join(m_extra) if m_extra else 'None'}")
        
    if st.button("Add Logic Rule"):
        if not p_name.strip() or not p_loci.strip():
            st.error("Both Phenotype Name and Loci are required.")
        else:
            new_rule = {
                "loci": [x.strip() for x in p_loci.split(",") if x.strip()]
            }
            if p_inactive.strip():
                new_rule["inactive_genes"] = [x.strip() for x in p_inactive.split(",") if x.strip()]
            if p_extra.strip():
                new_rule["extra_genes"] = [x.strip() for x in p_extra.split(",") if x.strip()]
            
            if p_priority != 50:
                new_rule["priority"] = int(p_priority)
                
            st.session_state.phenotype_dict[p_name.strip()] = new_rule
            st.rerun()


# --- Build & Export Section ---
metadata = {
    "name": name,
    "keyword": keyword,
    "genbank": genbank,
    "organism": organism,
    "taxon": int(taxon),
    "antigen": antigen,
    "pathway": pathway,
    "prefix": prefix,
    "version": version,
    "id_threshold": float(id_threshold),
    "doi": st.session_state.doi_list if len(st.session_state.doi_list) > 0 else ["TBD"],
    "owner": owner,
    "repo": repo,
    "branch": branch,
    "contact": st.session_state.contact_dict if len(st.session_state.contact_dict) > 0 else {"TBD": "TBD"}
}

if st.session_state.phenotype_dict:
    metadata["phenotype_logic"] = st.session_state.phenotype_dict

st.divider()
toml_string = toml.dumps(metadata)

download_filename = "metadata.toml" 
if genbank and genbank.endswith('.gbk'):
    download_filename = genbank.split('/')[-1].replace('.gbk', '.toml')

st.subheader("Export Options 🚀")
export_col1, export_col2 = st.columns([1, 1])

with export_col1:
    st.markdown("**Live Preview**")
    st.code(toml_string, language="toml")
    
    if is_valid_version and is_db_valid:
        st.download_button(
            label=f"⬇️ Download {download_filename}",
            data=toml_string,
            file_name=download_filename,
            mime="application/toml",
            use_container_width=True
        )
    elif not is_valid_version:
        st.button("⬇️ Download (Disabled - Version Error)", disabled=True, use_container_width=True)
    else:
        st.button("⬇️ Download (Disabled - Validation Failed)", disabled=True, use_container_width=True)

with export_col2:
    st.markdown(f"**Push to `{owner}/{repo}` ({branch})**")
    
    with st.container(border=True):
        gh_filepath = st.text_input("Filepath (e.g., folder/metadata.toml)", value=download_filename)
        gh_commit_msg = st.text_input(
            "Commit Message", value=f"Add metadata for {organism} {prefix}-types",
            help="You can use [conventional commits](https://github.com/tomdstanton/kaptive-db-template/tree/main#database-versioning--release-workflow-) to automatically version your database!"
        )
        gh_token = st.text_input("GitHub Personal Access Token (PAT)", type="password", help="Requires 'repo' scope.")
        
        can_push = is_valid_version and is_db_valid and gh_token and gh_filepath
        
        if st.button("🚀 Commit to GitHub", disabled=not can_push, type="primary", use_container_width=True):
            with st.spinner(f"Pushing to {branch}..."):
                success, message = push_to_github(
                    owner=owner, repo=repo, branch=branch, 
                    filepath=gh_filepath, content=toml_string, 
                    token=gh_token, commit_message=gh_commit_msg
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)
        
        if not gh_token:
            st.caption("🔑 *Enter a GitHub PAT to enable direct pushing.*")
