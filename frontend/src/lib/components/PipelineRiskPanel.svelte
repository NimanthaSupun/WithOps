<script>
  import { onMount } from 'svelte';
  import { pipelinePredictionApi } from '../api/pipelinePrediction';
  import { slide, fade } from 'svelte/transition';

  export let orgName = '';
  export let repoName = '';
  export let branch = 'main';
  export let author = '';
  export let filesChanged = 0;
  export let additions = 0;
  export let deletions = 0;
  export let commitMessage = '';
  
  // Support for injected prediction
  export let prediction = null;

  let loading = false;
  let error = null;

  async function fetchPrediction() {
    if (!orgName || !repoName || prediction) return;
    
    loading = true;
    error = null;
    
    try {
      const result = await pipelinePredictionApi.predict({
        org_name: orgName,
        repo_name: repoName,
        branch,
        author,
        files_changed: filesChanged,
        additions,
        deletions,
        commit_message: commitMessage
      });
      // The API returns the PredictResponse directly, no 'success' field wrapper
      prediction = result;
    } catch (e) {
      console.error('Prediction failed:', e);
      error = e.message;
    } finally {
      loading = false;
    }
  }

  $: if (orgName && repoName && !prediction && (filesChanged || additions || deletions)) {
    fetchPrediction();
  }

  const getRiskClass = (level) => {
    return `risk-${level?.toLowerCase() || 'unknown'}`;
  };
</script>

<div class="risk-panel {getRiskClass(prediction?.prediction?.risk_level)}">
  <div class="panel-header">
    <div class="header-left">
      <div class="status-indicator"></div>
      <h3 class="panel-title">AI PIPELINE RISK ANALYSIS</h3>
    </div>
    {#if loading}
      <div class="spinner-small"></div>
    {/if}
  </div>

  <div class="panel-body">
    {#if error}
      <div class="error-msg">
        <p>Prediction service unavailable: {error}</p>
        <button class="retry-btn" on:click={fetchPrediction}>Retry</button>
      </div>
    {:else if !prediction && !loading}
      <div class="empty-msg">
        Waiting for pipeline data...
      </div>
    {:else if prediction}
      <div in:fade={{ duration: 300 }}>
        <!-- Summary Section -->
        <div class="summary-section">
          <div class="prob-group">
            <div class="prob-label">FAILURE PROBABILITY</div>
            <div class="prob-value">
              {(prediction.prediction.failure_probability * 100).toFixed(0)}<span class="unit">%</span>
            </div>
          </div>
          <div class="risk-badge">
            {prediction.prediction.risk_level} Risk
          </div>
        </div>

        <!-- Risk Progress Bar -->
        <div class="risk-meter">
          <div 
            class="meter-fill"
            style="width: {prediction.prediction.failure_probability * 100}%"
          ></div>
        </div>

        <!-- Factors Section -->
        {#if prediction.risk_factors && prediction.risk_factors.length > 0}
          <div class="factors-section">
            <h4 class="section-title">KEY RISK FACTORS</h4>
            <div class="factors-list">
              {#each prediction.risk_factors as factor}
                <div class="factor-item">
                  <div class="factor-bar" style="opacity: {factor.importance * 0.8 + 0.2}"></div>
                  <div class="factor-content">
                    <div class="factor-header">
                      <span class="factor-name">{factor.factor}</span>
                      <span class="factor-impact">impact: {(factor.importance * 100).toFixed(0)}%</span>
                    </div>
                    <p class="factor-detail">{factor.detail}</p>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Recommendation -->
        <div class="recommendation-box">
          <div class="rec-header">
            <svg class="rec-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span class="rec-label">RECOMMENDATION</span>
          </div>
          <p class="rec-text">
            "{prediction.recommendation}"
          </p>
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer Info -->
  {#if prediction}
    <div class="panel-footer">
      <div class="model-info">
        MODEL v{prediction.model_info.version} • {prediction.model_info.type}
      </div>
      <div class="confidence">
        CONFIDENCE: {(prediction.prediction.confidence * 100).toFixed(0)}%
      </div>
    </div>
  {/if}
</div>

<style>
  .risk-panel {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    overflow: hidden;
    color: #f8fafc;
    transition: all 0.3s ease;
    box-shadow: 0 20px 40px -10px rgba(0,0,0,0.4);
  }

  .panel-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(90deg, rgba(255,255,255,0.03), transparent);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .status-indicator {
    width: 6px;
    height: 6px;
    background: #6366f1;
    border-radius: 50%;
    box-shadow: 0 0 8px #6366f1;
    animation: pulse 2s infinite;
  }

  .panel-title {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: rgba(255, 255, 255, 0.7);
  }

  .panel-body {
    padding: 1.5rem;
  }

  .summary-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 1.5rem;
  }

  .prob-label {
    font-size: 0.6rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.4);
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
  }

  .prob-value {
    font-family: var(--font-mono, monospace);
    font-size: 2.5rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.05em;
  }

  .prob-value .unit {
    font-size: 1.25rem;
    color: rgba(255, 255, 255, 0.3);
    margin-left: 0.1rem;
  }

  .risk-badge {
    padding: 0.375rem 0.75rem;
    border-radius: 99px;
    font-size: 0.65rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  /* Risk levels */
  .risk-low .risk-badge { color: #10b981; border-color: rgba(16, 185, 129, 0.2); background: rgba(16, 185, 129, 0.1); }
  .risk-low .meter-fill { background: #10b981; }
  .risk-low .factor-bar { background: #10b981; }

  .risk-medium .risk-badge { color: #f59e0b; border-color: rgba(245, 158, 11, 0.2); background: rgba(245, 158, 11, 0.1); }
  .risk-medium .meter-fill { background: #f59e0b; }
  .risk-medium .factor-bar { background: #f59e0b; }

  .risk-high .risk-badge { color: #f97316; border-color: rgba(249, 115, 22, 0.2); background: rgba(249, 115, 22, 0.1); }
  .risk-high .meter-fill { background: #f97316; }
  .risk-high .factor-bar { background: #f97316; }

  .risk-critical .risk-badge { color: #f43f5e; border-color: rgba(244, 63, 94, 0.2); background: rgba(244, 63, 94, 0.1); }
  .risk-critical .meter-fill { background: #f43f5e; }
  .risk-critical .factor-bar { background: #f43f5e; }

  .risk-meter {
    height: 4px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 99px;
    overflow: hidden;
    margin-bottom: 2rem;
  }

  .meter-fill {
    height: 100%;
    transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .section-title {
    font-size: 0.6rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.4);
    letter-spacing: 0.1em;
    margin-bottom: 1rem;
  }

  .factors-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 2rem;
  }

  .factor-item {
    display: flex;
    gap: 1rem;
    padding: 0.75rem;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid transparent;
    transition: all 0.2s ease;
  }

  .factor-item:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.05);
    transform: translateX(4px);
  }

  .factor-bar {
    width: 2px;
    height: 32px;
    border-radius: 99px;
    margin-top: 0.25rem;
  }

  .factor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
  }

  .factor-name {
    font-size: 0.8125rem;
    font-weight: 600;
  }

  .factor-impact {
    font-size: 0.6rem;
    color: rgba(255, 255, 255, 0.2);
    font-family: var(--font-mono, monospace);
  }

  .factor-detail {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
    line-height: 1.4;
  }

  .recommendation-box {
    background: rgba(99, 102, 241, 0.08);
    border: 1px solid rgba(99, 102, 241, 0.15);
    border-radius: 12px;
    padding: 1rem;
  }

  .rec-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .rec-icon {
    width: 14px;
    height: 14px;
    color: #818cf8;
  }

  .rec-label {
    font-size: 0.6rem;
    font-weight: 700;
    color: #818cf8;
    letter-spacing: 0.05em;
  }

  .rec-text {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.8);
    font-style: italic;
    line-height: 1.5;
  }

  .panel-footer {
    padding: 0.75rem 1.5rem;
    background: rgba(255, 255, 255, 0.02);
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .model-info, .confidence {
    font-size: 0.6rem;
    font-family: var(--font-mono, monospace);
    color: rgba(255, 255, 255, 0.2);
  }

  .empty-msg {
    padding: 3rem 0;
    text-align: center;
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.3);
    font-style: italic;
  }

  .spinner-small {
    width: 12px;
    height: 12px;
    border: 1.5px solid rgba(255,255,255,0.1);
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: rotate 1s linear infinite;
  }

  @keyframes rotate { to { transform: rotate(360deg); } }
  @keyframes pulse { 
    0%, 100% { opacity: 1; transform: scale(1); } 
    50% { opacity: 0.5; transform: scale(0.8); } 
  }
</style>
