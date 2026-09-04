<h1>Staging</h1>
<a id="readme-top"></a>

This staging folder contains 4 scripts, each one staging data from its original raw source into a staging schema:  

<h2>Directory Map</h2>

```Plaintext
DSNY-Analytics-Engineering-Accelerator/
├── [...]
└── transformer/
    ├── models/                
    │   └── stage/                                              <-- YOU ARE HERE
    │   │   ├── _src_to_stg_models.yml                          <-- YAML that defines external data sources
    │   │   ├── stg_balancing_authority_interchange.sql         <-- staging model for Balancing Authority Interchange data
    │   │   ├── stg_generation_energy_source.sql                <-- staging model for generation by energy source data
    │   │   ├── stg_regional_operating_metrics.sql              <-- staging model for aggregated regional operations data
    │   │   └── stg_subregional_demand.sql                      <-- staging model for demand by subregion data
    │   ├── intermediate/      
    │   └── mart/              
    └── [...]          
```

<h2>Key steps</h2>

<details>
<summary><strong style="font size 24px:";>Imports</strong></summary>

>
As always we need to bring in any packages we're using. In this case:
- `xxx` is used to ...
- `datetime` is used to create a timestamp for ...
- `xxx` is used for ...

```python
from xxx import xxx
from datetime import datetime
import xx
```
</details>

<details>
<summary><strong style="font size 24px;";>Script Explaination</strong></summary>

>
The script has two key functions:
- xxx(): lorem ipsum
- xxx(): lorem ipsum

```python
enter code here
```
</details>

<h2>Project Setup</h2>

Configuration considerations:

<h3>1. Clone the repository</h3>

```shell
git clone https://github.com/xxx/xxx.git
```

<h3>2. Move into the new directory</h3>

```shell
cd project_name
```

<h3>3. Create a virtual environment (optional)</h3>

```shell
python -m venv .venv
```

This step isn't strictly necessary but is good practice for isolation and keeping projects lean in terms of packages and so on.

<h3>4. Activate your virtual environment</h3>

For Windows users:

```shell
.venv\scripts\activate
```

For Mac users:

```shell
source .venv/bin/activate
```

Again, this isn't strictly necessary i.e. if you're not using a venv as outlined in the step above.

<h3>5. Install required packages</h3>

```shell
pip install -r requirements.txt
```

This will install project environment requirements.

<h3>999. Run Project</h3>

Instructions here

```shell
python main.py
```

This will run the script.
