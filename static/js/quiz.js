// static/js/quiz.js — version 4 (Flat list / Option B)

/**
 * Progressive/mobile-friendly quiz UI: present one question at a time, map numeric sliders to semantic buckets, then submit JSON
 */
document.addEventListener("DOMContentLoaded", () => {
  const questionsContainer = document.getElementById("quiz-questions");
  const form = document.getElementById("quiz-form");
  const nameInput = document.getElementById("name");
  const birthInput = document.getElementById("birthdate");
  const STORAGE_KEY = "mirror_profile_flat";

  // Local cached profile
  let localProfile = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") || { name: "", birthdate: "", last_answers: {} };
  if (localProfile.name) nameInput.value = localProfile.name;
  if (localProfile.birthdate) birthInput.value = localProfile.birthdate;

  // Pagination state
  let questions = [];
  let currentIndex = 0;
  let answers = {};

  function mapValueToBucket(v){
    const n = Number(v) || 0;
    if(n <= 2) return 'low';
    if(n === 3) return 'medium';
    return 'high';
  }

  function renderQuestion(index){
    questionsContainer.innerHTML = '';
    if(!questions || !questions.length) { questionsContainer.innerHTML = '<p class="small">No questions available.</p>'; return; }
    const q = questions[index];

    const wrapper = document.createElement('div'); wrapper.className = 'question';
    const label = document.createElement('div'); label.className = 'qtext'; label.textContent = `${index+1}. ${q.text}`;
    wrapper.appendChild(label);

    // slider
    const slider = document.createElement('input'); slider.type = 'range'; slider.min = 1; slider.max = 5; slider.value = (localProfile.last_answers[`q_${q.id}`] || 3);
    slider.id = `q_${q.id}`; slider.name = `q_${q.id}`; slider.dataset.category = q.category || 'general';
    const hint = document.createElement('div'); hint.className = 'small'; hint.textContent = `Value: ${slider.value} / 5`;
    slider.addEventListener('input', () => { hint.textContent = `Value: ${slider.value} / 5`; });
    wrapper.appendChild(slider); wrapper.appendChild(hint);

    // free-text choices (if choices provided)
    if(q.choices && Array.isArray(q.choices) && q.choices.length){
      const choicesDiv = document.createElement('div'); choicesDiv.className = 'choices small';
      q.choices.forEach((c, i)=>{
        const btn = document.createElement('button'); btn.type='button'; btn.className='button'; btn.style.padding='8px 12px'; btn.textContent = c;
        btn.addEventListener('click', ()=>{ slider.value = 4; hint.textContent = `Selected: ${c}`; answers[`q_${q.id}`] = c; });
        choicesDiv.appendChild(btn);
      });
      wrapper.appendChild(choicesDiv);
    }

    // nav
    const nav = document.createElement('div'); nav.style.display='flex'; nav.style.gap='10px'; nav.style.marginTop='12px'; nav.style.justifyContent='space-between';
    const back = document.createElement('button'); back.type='button'; back.className='button'; back.textContent='Back'; back.style.minWidth='110px';
    const next = document.createElement('button'); next.type='button'; next.className='button'; next.textContent = (index===questions.length-1)?'Submit':'Next'; next.style.minWidth='110px';
    back.disabled = (index===0);
    nav.appendChild(back); nav.appendChild(next);

    const progress = document.createElement('div'); progress.className='quiz-progress small'; progress.textContent = `Question ${index+1} of ${questions.length}`;
    wrapper.appendChild(progress);
    wrapper.appendChild(nav);

    back.addEventListener('click', ()=>{ saveCurrent(); if(currentIndex>0){ currentIndex--; renderQuestion(currentIndex);} });
    next.addEventListener('click', async ()=>{ saveCurrent(); if(currentIndex < questions.length-1){ currentIndex++; renderQuestion(currentIndex);} else { await submitQuiz(); } });

    function saveCurrent(){
      const val = slider.value;
      // if answers stores free-text from choices, preserve; else map numeric
      if(answers[`q_${q.id}`] && typeof answers[`q_${q.id}`] === 'string' && answers[`q_${q.id}`].length>0) {
        // leave as-is
      } else {
        answers[`q_${q.id}`] = Number(val);
      }
      localProfile.last_answers[`q_${q.id}`] = Number(val);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(localProfile));
    }

    questionsContainer.appendChild(wrapper);
    // ensure visible
    window.scrollTo({top: 0, behavior: 'smooth'});
  }

  async function loadQuestions(){
    try{
      const res = await fetch('/quizdata');
      const data = await res.json();
      questions = data.questions || [];
      currentIndex = 0; answers = {};
      renderQuestion(0);
    }catch(e){ console.warn('Failed loading questions', e); questionsContainer.innerHTML = '<p class="small">Could not load questions.</p>'; }
  }

  function createLoadingOverlay(){
    const existing = document.getElementById('mm-loading-overlay'); if(existing) return existing;
    const o = document.createElement('div'); o.id='mm-loading-overlay'; o.innerHTML = `<div class="mm-loader"><div class="spinner"></div><div class="mm-text">Revealing your reflection…</div></div>`;
    Object.assign(o.style, { position: 'fixed', inset: '0', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999 }); document.body.appendChild(o); return o;
  }

  async function submitQuiz(){
    // map numeric answers to semantic buckets for server-side process_quiz
    const mapped = {};
    for(const k in answers){
      const v = answers[k];
      if(typeof v === 'number') mapped[k.replace(/^q_/, '')] = mapValueToBucket(v);
      else mapped[k.replace(/^q_/, '')] = v;
    }

    const profile = {
      name: (nameInput.value || 'Wanderer').trim(),
      birthdate: birthInput.value || '2000-01-01',
      quiz: mapped
    };

    // Save local profile
    localProfile.name = profile.name; localProfile.birthdate = profile.birthdate; localProfile.last_answers = answers; localStorage.setItem(STORAGE_KEY, JSON.stringify(localProfile));

    // Submit
    const overlay = createLoadingOverlay(); form.querySelectorAll('input,button').forEach(el=>el.setAttribute('disabled','disabled'));
    try{
      const res = await fetch('/submit', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(profile) });
      try{ const data = await res.json(); if(data && data.fortune) localStorage.setItem('last_fortune', data.fortune); }catch(e){}
    }catch(e){ console.warn('submit error', e); }
    finally{ window.location.href = '/fortune'; }
  }

  // initial load
  loadQuestions();
});
