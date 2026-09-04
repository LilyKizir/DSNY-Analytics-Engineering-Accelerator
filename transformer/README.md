<h1>Tranformer</h1>
<a id="readme-top"></a>

This folder contains a dbt project that pulls raw data from snowflake and transforms it, through a series of models, into BI ready tables.

<h2>Directory Map</h2>

```Plaintext
DSNY-Analytics-Engineering-Accelerator/
├── [everything else]
└── transformer/               <-- YOU ARE HERE
    ├── models/
    ├── macros/
    ├── tests/
    ├── dbt_project.yml
    └── profiles.yml          
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
