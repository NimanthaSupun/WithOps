🎯 DSOMM Maturity Score Calculation - Complete Explanation
📁 Your Example: 1 Project Folder → 1 Repository → 5 Workflows
Your workflows in workflow:

ci-caller.yml - Calls reusable workflow
gitleaks.yaml - Secret scanning with Gitleaks
reusable-ci.yml - Reusable workflow definition
test.yml - Basic CI pipeline
trufflehog.yaml - PR title enforcement (not a security tool)

STEP-BY-STEP SCORE CALCULATION
STEP 1: Tool Detection Phase
The system scans each workflow file looking for security tool patterns:

Workflow 1: gitleaks.yaml

docker run --rm -v "$(pwd)/$repo:/repo" \
  ghcr.io/gitleaks/gitleaks:latest detect \  # ← DETECTED!

✅ Detected: gitleaks → Secret Scanning Tool

Workflow 2: trufflehog.yaml
name: trufflehog  # ← Pattern match!

✅ Detected: trufflehog → Secret Scanning Tool

Workflow 3: reusable-ci.yml
on:
  workflow_call:  # ← This is a REUSABLE workflow!

✅ Detected: Reusable workflow pattern

Workflow 4: test.yml & ci-caller.yml
No security tools detected
Basic CI/CD functionality

STEP 2: Aggregate Detected Practices
After scanning all 5 workflows, the system aggregates:

detected_practices = {
    'sast_tools': [],                    # ❌ No SAST tools
    'sca_tools': [],                     # ❌ No SCA tools  
    'dast_tools': [],                    # ❌ No DAST tools
    'secret_scanning_tools': [           # ✅ 2 tools found
        'gitleaks',
        'trufflehog'
    ],
    'container_scanning_tools': [],      # ❌ No container scanning
    
    # Process practices
    'has_pr_workflows': True,            # ✅ trufflehog runs on PR
    'uses_reusable_workflows': True,     # ✅ reusable-ci.yml exists
    'pins_action_versions': True,        # ✅ uses: actions/checkout@v4.2.2
    
    'repos_with_workflows': 1,
    'total_repos': 1
}


STEP 3: Calculate Technology Domain Scores
The system evaluates 5 technology activities:

Activity 1: SAST (Static Application Security Testing)
def _assess_sast(tools):
    # Your detected SAST tools: []
    
    if not tools:  # You have NO SAST tools
        level = 0
        score = 0
        description = "No SAST tools"
    
    return {
        'activity_name': 'Static Application Security Testing (SAST)',
        'level': 0,
        'score': 0,  # 0 points
        'detected_tools': [],
        'status': 'Not Started'
    }


📊 SAST Score: 0/100 ❌

Activity 2: SCA (Software Composition Analysis)

def _assess_sca(tools):
    # Your detected SCA tools: []
    
    if not tools:  # You have NO SCA tools
        level = 0
        score = 0
        description = "No SCA tools"
    
    return {
        'level': 0,
        'score': 0,  # 0 points
        'detected_tools': []
    }

📊 SCA Score: 0/100 ❌

Activity 3: DAST (Dynamic Application Security Testing)

def _assess_dast(tools):
    # Your detected DAST tools: []
    
    if not tools:
        level = 0
        score = 0
    
    return {
        'level': 0,
        'score': 0  # 0 points
    }
📊 DAST Score: 0/100 ❌

Activity 4: Secret Scanning ⭐

def _assess_secret_scanning(tools):
    # Your detected tools: ['gitleaks', 'trufflehog']
    
    advanced_tools = {'gitleaks', 'trufflehog'}  # Both are advanced
    
    if len(tools) >= 2:  # ✅ You have 2 tools!
        level = 3
        score = 100  # Maximum score!
        description = "Pre-commit hooks preventing secret commits"
    
    return {
        'activity_name': 'Secret Scanning',
        'level': 3,
        'score': 100,  # 100 points! ✅
        'detected_tools': ['gitleaks', 'trufflehog'],
        'status': 'Fully Optimized'
    }

📊 Secret Scanning Score: 100/100 ✅✅✅

Activity 5: Container Scanning


def _assess_container_scanning(tools):
    # Your detected tools: []
    
    if not tools:
        level = 0
        score = 0
    
    return {
        'level': 0,
        'score': 0  # 0 points
    }

📊 Container Scanning Score: 0/100 ❌

technology_scores = {
    'sast': 0,
    'sca': 0,
    'dast': 0,
    'secret_scanning': 100,  # ⭐ Only this scored!
    'container_scanning': 0
}

# Calculate average
technology_avg = (0 + 0 + 0 + 100 + 0) / 5 = 20.0

🎯 Technology Domain Score: 20/100 (Level 0)


STEP 4: Calculate Process Domain Scores
Activity 1: CI/CD Integration

def _assess_ci_cd(detected_practices, workflows_count, has_ci_cd):
    # Your data:
    workflows_count = 5
    has_ci_cd = True  # You have workflows
    has_pr_workflows = True  # trufflehog.yaml runs on PR
    has_security_tools = True  # You have secret scanning
    
    if has_pr_workflows and has_security_tools and workflows_count >= 3:
        level = 3
        score = 100  # ✅ Comprehensive automation!
    
    return {
        'activity_name': 'DevSecOps Factory / CI/CD Integration',
        'level': 3,
        'score': 100,  # 100 points!
        'workflows_count': 5,
        'status': 'Fully Optimized'
    }

📊 CI/CD Integration Score: 100/100 ✅✅✅



Activity 2: Branch Protection
def _assess_branch_protection(detected_practices):
    # Your data (assuming no branch protection detected):
    has_protection = False
    
    if not has_protection:
        level = 0
        score = 0
    
    return {
        'level': 0,
        'score': 0  # 0 points
    }

📊 Branch Protection Score: 0/100 ❌
Activity 3: Reusable Workflows

def _assess_reusable_workflows(detected_practices):
    # Your data:
    uses_reusable = True  # ✅ You have reusable-ci.yml
    
    if uses_reusable:
        level = 2
        score = 75  # Centralized workflows!
    
    return {
        'activity_name': 'Reusable Security Components',
        'level': 2,
        'score': 75,  # 75 points!
        'status': 'Implemented'
    }

📊 Reusable Workflows Score: 75/100 ✅✅

Process Domain Total:
process_scores = {
    'ci_cd_integration': 100,  # ⭐
    'branch_protection': 0,
    'reusable_components': 75  # ⭐
}

# Calculate average
process_avg = (100 + 0 + 75) / 3 = 58.33

🎯 Process Domain Score: 58.33/100 (Level 1)


STEP 5: Calculate Overall Maturity Score
def calculate_maturity():
    technology_avg = 20.0    # From Step 3
    process_avg = 58.33      # From Step 4
    
    # Weighted calculation (Technology 60%, Process 40%)
    overall_maturity = (
        technology_avg * 0.6 +    # 20 × 0.6 = 12.0
        process_avg * 0.4         # 58.33 × 0.4 = 23.33
    )
    
    overall_maturity = 12.0 + 23.33 = 35.33
    
    # Convert to level
    if overall_maturity >= 90:
        maturity_level = 3  # Fully Optimized
    elif overall_maturity >= 60:
        maturity_level = 2  # Managed/Implemented
    elif overall_maturity >= 30:
        maturity_level = 1  # Partially Implemented ← YOUR LEVEL
    else:
        maturity_level = 0  # Not Started
    
    return {
        'overall_maturity_score': 35.33,
        'maturity_level': 1,
        'maturity_label': 'Partially Implemented (Initial)',
        'domain_scores': {
            'technology': {
                'score': 20.0,
                'level': 0,
                'activities': {
                    'sast': {'level': 0, 'score': 0},
                    'sca': {'level': 0, 'score': 0},
                    'dast': {'level': 0, 'score': 0},
                    'secret_scanning': {'level': 3, 'score': 100},
                    'container_scanning': {'level': 0, 'score': 0}
                }
            },
            'process': {
                'score': 58.33,
                'level': 1,
                'activities': {
                    'ci_cd_integration': {'level': 3, 'score': 100},
                    'branch_protection': {'level': 0, 'score': 0},
                    'reusable_components': {'level': 2, 'score': 75}
                }
            }
        }
    }

📊 FINAL SCORE BREAKDOWN FOR YOUR WORKFLOWS

Category	Activity	Detected Tools	Score	Level
Technology (60%)			20/100	0
SAST	None	0	0 ❌
SCA	None	0	0 ❌
DAST	None	0	0 ❌
Secret Scanning	gitleaks, trufflehog	100	3 ✅
Container Scanning	None	0	0 ❌
Process (40%)			58.33/100	1
CI/CD Integration	5 workflows, PR checks	100	3 ✅
Branch Protection	Not enabled	0	0 ❌
Reusable Workflows	reusable-ci.yml	75	2 ✅

🎯 Overall Maturity:
Score: 35.33/100
Level: 1 (Partially Implemented)
Label: "Initial - Partially Implemented"

