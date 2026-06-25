document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const searchBtn = document.getElementById('search-btn');
    const btnText = searchBtn.querySelector('.btn-text');
    const btnSpinner = searchBtn.querySelector('.btn-spinner');
    
    const loading = document.getElementById('loading');
    const resultsPanel = document.getElementById('results-panel');
    
    const resultQuestion = document.getElementById('result-question');
    const detectedEntities = document.getElementById('detected-entities');
    const resolvedArtifacts = document.getElementById('resolved-artifacts');
    const traversalGraph = document.getElementById('traversal-graph');
    const evidenceChunks = document.getElementById('evidence-chunks');
    const synthesizedAnswer = document.getElementById('synthesized-answer');
    
    // Step narrative elements
    const step1Narrative = document.getElementById('step-1-narrative');
    const step2Narrative = document.getElementById('step-2-narrative');
    const step3Narrative = document.getElementById('step-3-narrative');
    const step4Narrative = document.getElementById('step-4-narrative');
    const step5Narrative = document.getElementById('step-5-narrative');
    
    // Add event listeners to suggestion tags
    document.querySelectorAll('.suggestion-tag').forEach(tag => {
        tag.addEventListener('click', (e) => {
            e.preventDefault();
            const question = tag.getAttribute('data-q');
            queryInput.value = question;
            submitQuery(question);
        });
    });

    // Form submission
    queryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const question = queryInput.value.trim();
        if (question) {
            submitQuery(question);
        }
    });

    async function submitQuery(question) {
        setLoading(true);
        clearResults();
        
        try {
            const encodedQ = encodeURIComponent(question);
            const response = await fetch(`/api/query?q=${encodedQ}`);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            renderResults(data);
            
        } catch (error) {
            console.error('Error retrieving query results:', error);
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        if (isLoading) {
            btnText.style.display = 'none';
            btnSpinner.style.display = 'inline-block';
            searchBtn.disabled = true;
            queryInput.disabled = true;
            loading.style.display = 'flex';
            resultsPanel.style.display = 'none';
        } else {
            btnText.style.display = 'inline-block';
            btnSpinner.style.display = 'none';
            searchBtn.disabled = false;
            queryInput.disabled = false;
            loading.style.display = 'none';
        }
    }

    function clearResults() {
        resultQuestion.textContent = '';
        detectedEntities.innerHTML = '';
        resolvedArtifacts.innerHTML = '';
        traversalGraph.innerHTML = '';
        evidenceChunks.innerHTML = '';
        synthesizedAnswer.textContent = '';
        
        // Reset narratives
        step1Narrative.textContent = 'Scanning...';
        step2Narrative.textContent = 'Searching...';
        step3Narrative.textContent = 'Traversing...';
        step4Narrative.textContent = 'Gathering...';
        step5Narrative.textContent = 'Synthesizing...';
    }

    function showError(message) {
        clearResults();
        resultQuestion.textContent = 'Retrieval Failure';
        step5Narrative.innerHTML = `<span style="color: #ef4444; font-weight: 600;">Error: ${message}</span>`;
        synthesizedAnswer.textContent = 'Please check if the API server has crashed or address is unreachable.';
        resultsPanel.style.display = 'flex';
    }

    function renderResults(data) {
        // Set Question
        resultQuestion.textContent = data.question || '';

        // Helper map
        const artifactMap = {};
        if (data.artifacts) {
            data.artifacts.forEach(art => {
                artifactMap[art.id] = art;
            });
        }

        // Render Step 1: Entities
        if (data.entities && data.entities.length > 0) {
            const entNames = data.entities.map(e => `<strong>${e.canonical_name}</strong> (a ${e.entity_type.toLowerCase()})`);
            step1Narrative.innerHTML = `We scanned your question and spotted key clues: ${entNames.join(' and ')}. These will act as our target starting terms.`;

            data.entities.forEach(ent => {
                const badge = document.createElement('div');
                badge.className = 'badge entity';
                
                let colorHex = '#10b981'; // Green
                if (ent.entity_type === 'PERSON') colorHex = '#10b981';
                else if (ent.entity_type === 'LOCATION') colorHex = '#0ea5e9';
                else if (ent.entity_type === 'CONCEPT') colorHex = '#a855f7';
                else if (ent.entity_type === 'ORGANIZATION') colorHex = '#f59e0b';
                
                badge.style.borderLeft = `3px solid ${colorHex}`;
                badge.innerHTML = `
                    <span class="badge-icon">◉</span>
                    <span class="badge-label">${ent.canonical_name}</span>
                    <span class="badge-type" style="font-size: 9px; color: var(--text-muted); margin-left: 4px;">[${ent.entity_type}]</span>
                `;
                detectedEntities.appendChild(badge);
            });
        } else {
            step1Narrative.textContent = 'We scanned your question but did not detect any known keywords or entities.';
            detectedEntities.innerHTML = '<span class="no-data">No search targets detected.</span>';
        }

        // Render Step 2: Resolved Entry Artifacts
        if (data.artifacts && data.artifacts.length > 0) {
            const artNames = data.artifacts.map(a => `<strong>${a.title}</strong>`);
            step2Narrative.innerHTML = `We opened the relevant records matching our targets to start the search: ${artNames.slice(0, 2).join(' and ')}.`;
            
            data.artifacts.forEach(art => {
                const badge = document.createElement('div');
                badge.className = 'badge artifact';
                badge.style.borderLeft = `3px solid var(--color-blue)`;
                badge.innerHTML = `
                    <span class="badge-icon">📄</span>
                    <span class="badge-label">${art.title}</span>
                `;
                resolvedArtifacts.appendChild(badge);
            });
        } else {
            step2Narrative.textContent = 'We could not find any records matching the parsed clues.';
            resolvedArtifacts.innerHTML = '<span class="no-data">No resolved documentation files.</span>';
        }

        // Render Step 3: Traversal Graph
        if (data.paths && data.paths.length > 0) {
            let primaryPath = data.paths[0];
            data.paths.forEach(p => {
                if (p.length > primaryPath.length) {
                    primaryPath = p;
                }
            });

            const pathTitles = primaryPath.map(nodeId => {
                const artObj = artifactMap[nodeId];
                return artObj ? artObj.title : nodeId;
            });

            if (pathTitles.length >= 2) {
                const hops = pathTitles.map(t => `<strong>${t}</strong>`).join(' → ');
                step3Narrative.innerHTML = `Because the starting page didn't contain all answers directly, we followed the link citations to complete a traversal path: ${hops}.`;
            } else {
                step3Narrative.innerHTML = `We found a direct answer within the <strong>${pathTitles[0]}</strong> page, so no multi-hop jumping was needed.`;
            }

            primaryPath.forEach((nodeId, idx) => {
                const artObj = artifactMap[nodeId];
                const displayName = artObj ? artObj.title : nodeId;

                const nodeEl = document.createElement('div');
                nodeEl.className = 'graph-node';
                nodeEl.textContent = displayName;
                traversalGraph.appendChild(nodeEl);

                if (idx < primaryPath.length - 1) {
                    const arrowEl = document.createElement('div');
                    arrowEl.className = 'graph-arrow';
                    arrowEl.innerHTML = `
                        <span class="arrow-line">→</span>
                        <span class="arrow-label">links_to</span>
                    `;
                    traversalGraph.appendChild(arrowEl);
                }
            });
        } else if (data.artifacts && data.artifacts.length > 0) {
            const startTitle = data.artifacts[0].title;
            step3Narrative.innerHTML = `We read the documentation page <strong>${startTitle}</strong> directly. No further reference links were traversed.`;
            
            const nodeEl = document.createElement('div');
            nodeEl.className = 'graph-node';
            nodeEl.textContent = startTitle;
            traversalGraph.appendChild(nodeEl);
        } else {
            step3Narrative.textContent = 'No traversal trail could be generated.';
            traversalGraph.innerHTML = '<span class="no-data">No path traversed.</span>';
        }

        // Render Step 4: Evidence Chunks
        if (data.chunks && data.chunks.length > 0) {
            step4Narrative.innerHTML = `We reviewed all pages along the navigation route and extracted <strong>${data.chunks.length} specific reference sentences</strong> containing the core answers:`;

            data.chunks.forEach(chunk => {
                const chunkCard = document.createElement('div');
                chunkCard.className = 'chunk-card';
                
                const parentArt = artifactMap[chunk.artifact_id];
                const sourceTitle = parentArt ? parentArt.title : 'Database Excerpt';
                
                let displayId = chunk.id;
                try {
                    const num = chunk.id.split('_')[1];
                    if (num) displayId = `Excerpt #${num}`;
                } catch(e) {}

                chunkCard.innerHTML = `
                    <div class="chunk-header">
                        <span class="chunk-id">${displayId}</span>
                        <span class="chunk-source">${sourceTitle}</span>
                    </div>
                    <p class="chunk-content">${chunk.content}</p>
                `;
                evidenceChunks.appendChild(chunkCard);
            });
        } else {
            step4Narrative.textContent = 'No exact textual evidence could be collected.';
            evidenceChunks.innerHTML = '<span class="no-data">No evidence chunks retrieved.</span>';
        }

        // Render Step 5: Answer
        step5Narrative.innerHTML = `We read the collected evidence and compiled a simple explanation that tells the complete story:`;
        synthesizedAnswer.textContent = data.answer || 'No answer generated.';

        resultsPanel.style.display = 'flex';
    }
});
