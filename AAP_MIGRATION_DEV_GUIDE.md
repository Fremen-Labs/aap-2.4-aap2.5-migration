# AAP 2.4 to 2.5 Migration: Developer Guide

This guide details the iterative process for expanding the AAP 2.4 export capabilities and mapping them to AAP 2.5 Config-as-Code (CaC) formats.

## Overview of the Pattern

The migration tooling follows a specific pattern:
1.  **Extract**: Ansible playbook (`2.4_export_single_org.yml`) queries the AAP 2.4 API and saves raw JSON to `_export_24/`.
2.  **Enrich**: **(The Developer Loop)** If an object (e.g., a Job Template) normally returns "related" items as just a URL (e.g., `/api/v2/job_templates/5/credentials/`), the playbook must be updated to follow that link and "hydrate" the detailed data into the export.
3.  **Transform**: Python script (`scripts/transform_24_to_25.py`) reads the enriched JSON and maps it to the AAP 2.5 YAML schema in `_cac_25/`.

---

## The Iterative Developer Process

Follow these steps to add support for new resources or deepen existing exports (e.g., adding Credentials to Job Templates, or Schedules).

### 1. Run Baseline Export
Run the current export playbook to see what we have.

```bash
export AAP24_USERNAME="your_username"
export AAP24_PASSWORD="your_password"
# Make sure your inventory or extra vars provide 'aap24_host' and 'export_org_name'
ansible-playbook playbooks/2.4_export_single_org.yml -e "export_org_name=MyOrg"
```

### 2. Inspect the JSON Output
Look at the generated files in `_export_24/`. Open a file like `job_templates.json`.

*   **Look for URLs instead of Data**: AAP 2.4 API often uses "summary fields" or "related" links.
    *   *Example*: You might see `"related": { "credentials": "/api/v2/job_templates/X/credentials/" }`.
    *   *Goal*: If we need the actual data from that link to configure AAP 2.5, we must fetch it.

### 3. Update the Export Playbook (`2.4_export_single_org.yml`)
If you found related data that needs fetching, you must add an **enrichment loop** to the playbook.

**Reference Implementation**: Look at the **"Fetch Related Hosts --> Inventories Only"** task (around line 141) in `playbooks/2.4_export_single_org.yml`.

**Pattern to Implement:**
1.  Identify the main loop where resources are processed.
2.  Add a `when` condition for your specific resource (e.g., `resource == 'job_templates'`).
3.  Use `ansible.builtin.uri` to fetch the related URL for *each* item in the current page results.
4.  Use `ansible.builtin.set_fact` (with Jinja2) to merge the new data back into the original item list.

**Example (Pseudo-code for adding Credentials to Job Templates):**

```yaml
- name: Fetch Related Credentials for Job Templates
  ansible.builtin.uri:
    url: "{{ controller_hostname }}{{ item.related.credentials }}?page_size=200"
    method: GET
    # ... auth params ...
  register: related_credentials_lookup
  loop: "{{ org_page.json.results }}"
  when: resource == 'job_templates'

- name: Merge Credentials Data Into Job Templates
  ansible.builtin.set_fact:
    final_results: >-
      {%- set output = [] -%}
      {%- for item in org_page.json.results -%}
        {# Extract the credentials list from the lookup result #}
        {%- set creds = related_credentials_lookup.results[loop.index0].json.results | default([]) -%}
        {# Merge it into a new key, e.g., 'related_credentials_data' #}
        {%- set _ = item.update({'related_credentials_data': creds}) -%}
        {%- set _ = output.append(item) -%}
      {%- endfor -%}
      {{ output }}
  when: resource == 'job_templates'
```

### 4. Verify Export Data
Run the playbook again. Check `_export_24/job_templates.json`.
*   **Result**: You should now see a `related_credentials_data` list inside each job template object efficiently populated with the actual credential details.

### 5. Update the Transform Script (`scripts/transform_24_to_25.py`)
Now that the JSON contains the data, you need to map it to the AAP 2.5 schema.

1.  Open `scripts/transform_24_to_25.py`.
2.  Locate the normalizer function for your resource (e.g., `normalize_job_template`).
3.  Update the logic to read from your new enriched field (`related_credentials_data`) instead of the shallow summary fields.

**Example Update:**

```python
def normalize_job_template(t: Mapping[str, Any]) -> Dict[str, Any]:
    # ... existing code ...
    
    # OLD: reading from shallow summary
    # creds_source = t.get("summary_fields", {}).get("credentials", [])
    
    # NEW: reading from our enriched data
    creds_source = t.get("related_credentials_data") or []
    
    # Mapping logic remains the same (resolving names, etc.)
    # ...
```

### 6. Run Transform & Validate
Execute the Python script to generate the final YAML.

```bash
python3 scripts/transform_24_to_25.py
```

Check `_cac_25/controller_job_templates.yml`.
*   **Verification**: Ensure the `credentials` list in the YAML is accurate and contains the *names* of the credentials as expected by AAP 2.5.

### 7. Test Import (Optional but Recommended)
Use the `infra.aap_configuration` collection to try applying these files to a developer instance of AAP 2.5 to ensure the schema is valid and the references resolve correctly.
