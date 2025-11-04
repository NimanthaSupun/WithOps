<script>
  import OrganizationCollaboration from './OrganizationCollaboration.svelte';
  
  export const modelId = '';
  export let orgName = '';
  export let currentUser = null;
  
  let showOrganizationCollaboration = false;
  
  function openCollaborationModal() {
    showOrganizationCollaboration = true;
  }
</script>

<button 
  class="share-button"
  on:click={openCollaborationModal}>
   Invite Team
</button>

<OrganizationCollaboration 
  bind:isOpen={showOrganizationCollaboration}
  organization={orgName}
  {currentUser}
/>

<style>
  .share-button {
    background: #3b82f6;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
  }
</style>
