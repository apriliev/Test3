// Mock Data - in memory storage
const mockData = {
  managers: [
    { id: 1, name: "Иван", health_score: 89, status: "potential", emoji: "👨‍💼" },
    { id: 2, name: "Ирина", health_score: 65, status: "cold", emoji: "👩‍💼" },
    { id: 3, name: "Артем", health_score: 74, status: "potential", emoji: "👨‍💼" },
    { id: 4, name: "Мария", health_score: 30, status: "optimism", emoji: "👩‍💼" }
  ],
  
  deals: [
    {
      id: 1,
      title: "Сделка №1 - ООО Техцентр",
      manager: "Иван",
      amount: 250000,
      stage: "negotiation",
      health_positive: [
        "Может быть в статусе ещё 18 дней",
        "Укладывается в цикл сделки",
        "Есть контакт в карточке"
      ],
      health_negative: [],
      last_call: "3 дня назад",
      probability: 85
    },
    {
      id: 2,
      title: "Сделка №2 - ЗАО Промторг",
      manager: "Ирина",
      amount: 450000,
      stage: "presentation",
      health_positive: ["Укладывается в цикл сделки"],
      health_negative: [
        "Задача просрочена на 2 дня",
        "Нет компании в карточке"
      ],
      last_call: "10 дней назад",
      probability: 45
    },
    {
      id: 3,
      title: "Сделка №3 - ИП Стройсервис",
      manager: "Артем",
      amount: 180000,
      stage: "tender",
      health_positive: ["Есть контакт в карточке"],
      health_negative: ["Задача просрочена на 5 дней"],
      last_call: "7 дней назад",
      probability: 60
    },
    {
      id: 4,
      title: "Сделка №4 - ООО МегаБизнес",
      manager: "Мария",
      amount: 920000,
      stage: "lost",
      health_positive: [],
      health_negative: [
        "Нет компании в карточке",
        "Не звонили 15 дней"
      ],
      last_call: "15 дней назад",
      probability: 15
    },
    {
      id: 5,
      title: "Сделка №5 - ООО Альфа",
      manager: "Иван",
      amount: 350000,
      stage: "negotiation",
      health_positive: ["Есть контакт в карточке", "Укладывается в цикл сделки"],
      health_negative: [],
      last_call: "1 день назад",
      probability: 75
    }
  ],
  
  calls_data: [
    {
      id: 1,
      filename: "call_20241031_001.mp3",
      manager: "Иван",
      client: "ООО Техцентр",
      duration: "12:45",
      date: "2025-10-31",
      transcription: "Менеджер: Добрый день! Это компания РУБИ ЧАТ. Как дела? Клиент: Здравствуйте, спасибо, всё хорошо. Менеджер: Я звоню по вашему запросу о нашем сервисе управления продажами. Клиент: Да, мне интересно узнать подробнее. Менеджер: Наш AI-сервис автоматизирует контроль вашей воронки продаж, экономит 80% времени руководителя на анализ CRM.",
      quality_score: 18,
      scores: { politeness: 5, understanding: 5, solution: 4, closing: 4 },
      sentiment: "positive",
      key_phrases: ["автоматизирует контроль", "80% времени", "воронка продаж"]
    },
    {
      id: 2,
      filename: "call_20241030_002.mp3",
      manager: "Ирина",
      client: "ЗАО Промторг",
      duration: "08:22",
      date: "2025-10-30",
      transcription: "Менеджер: Привет, это Ирина из РУБИ ЧАТ. Клиент: Привет. Менеджер: Я звоню по поводу вашей заявки. Клиент: Хорошо, слушаю. Менеджер: У нас есть интересный модуль для аудита воронки. Клиент: Может, напишешь мне всю информацию? Менеджер: Конечно, отправлю КП сегодня.",
      quality_score: 12,
      scores: { politeness: 4, understanding: 3, solution: 2, closing: 3 },
      sentiment: "neutral",
      key_phrases: ["аудита воронки", "модуль"]
    }
  ],
  
  kpi: {
    plan_month: 3560000,
    fact_current: 1860000,
    potential: 1250000,
    deficit: 450000,
    days_left: 12,
    deal_stats: {
      without_tasks: 38,
      overdue_tasks: 46,
      stuck_deals: 0,
      lost_deals: 29
    }
  },
  
  chatHistory: []
};

// State
let currentModule = 'dashboard';
let currentPeriod = 'month';
let currentManager = 'all';
let isLoggedIn = false;

// Utility Functions
function formatNumber(num) {
  return new Intl.NumberFormat('ru-RU').format(num);
}

function formatCurrency(num) {
  return formatNumber(num) + ' ₽';
}

function getHealthClass(score) {
  if (score >= 75) return 'high';
  if (score >= 50) return 'medium';
  return 'low';
}

function getStageLabel(stage) {
  const stages = {
    negotiation: 'Переговоры',
    presentation: 'Презентация',
    tender: 'Тендер',
    lost: 'Проиграна'
  };
  return stages[stage] || stage;
}

// Login
function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value;
  const password = document.getElementById('loginPassword').value;
  
  if (username === 'admin' && password === 'admin') {
    isLoggedIn = true;
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('mainApp').style.display = 'flex';
    initializeApp();
  } else {
    alert('Неверный логин или пароль');
  }
}

function handleLogout() {
  isLoggedIn = false;
  document.getElementById('loginScreen').style.display = 'flex';
  document.getElementById('mainApp').style.display = 'none';
  document.getElementById('loginUsername').value = '';
  document.getElementById('loginPassword').value = '';
}

// Module Navigation
function switchModule(moduleName) {
  currentModule = moduleName;
  
  // Update nav items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
    if (item.dataset.module === moduleName) {
      item.classList.add('active');
    }
  });
  
  // Update modules
  document.querySelectorAll('.module').forEach(module => {
    module.classList.remove('active');
  });
  document.getElementById(`${moduleName}Module`).classList.add('active');
  
  // Load module data
  loadModuleData(moduleName);
}

function loadModuleData(moduleName) {
  switch(moduleName) {
    case 'dashboard':
      renderDashboard();
      break;
    case 'audit':
      renderAuditTable();
      break;
    case 'calls':
      renderCallsHistory();
      break;
    case 'pulse':
      renderPulseGrid();
      break;
    case 'assistant':
      // Chat is already initialized
      break;
  }
}

// Dashboard Module
function renderDashboard() {
  const kpi = mockData.kpi;
  
  // Update KPI cards
  document.getElementById('kpiPlan').textContent = formatCurrency(kpi.plan_month);
  document.getElementById('kpiFact').textContent = formatCurrency(kpi.fact_current);
  document.getElementById('kpiPotential').textContent = formatCurrency(kpi.potential);
  document.getElementById('kpiDeficit').textContent = formatCurrency(kpi.deficit);
  
  // Update progress
  const progress = Math.round((kpi.fact_current / kpi.plan_month) * 100);
  document.getElementById('planProgress').style.width = progress + '%';
  
  // Update stats
  document.getElementById('statWithoutTasks').textContent = kpi.deal_stats.without_tasks;
  document.getElementById('statOverdue').textContent = kpi.deal_stats.overdue_tasks;
  document.getElementById('statLost').textContent = kpi.deal_stats.lost_deals;
  document.getElementById('statStuck').textContent = kpi.deal_stats.stuck_deals;
  
  // Render managers
  renderManagers();
}

function renderManagers() {
  const grid = document.getElementById('managersGrid');
  grid.innerHTML = '';
  
  mockData.managers.forEach(manager => {
    const healthClass = getHealthClass(manager.health_score);
    const card = document.createElement('div');
    card.className = 'manager-card';
    card.innerHTML = `
      <div class="manager-header">
        <div class="manager-avatar">${manager.emoji}</div>
        <div class="manager-info">
          <h4>Менеджер ${manager.name}</h4>
          <p class="text-secondary">Отдел продаж</p>
        </div>
      </div>
      <div class="manager-health">
        <div class="health-score ${healthClass}">${manager.health_score}</div>
        <div class="health-label">Здоровье сделок</div>
      </div>
    `;
    grid.appendChild(card);
  });
}

// Audit Module
function renderAuditTable() {
  const tbody = document.getElementById('dealsTableBody');
  tbody.innerHTML = '';
  
  let deals = mockData.deals;
  if (currentManager !== 'all') {
    const manager = mockData.managers.find(m => m.id === parseInt(currentManager));
    if (manager) {
      deals = deals.filter(d => d.manager === manager.name);
    }
  }
  
  deals.forEach(deal => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><div class="deal-title">${deal.title}</div></td>
      <td>${deal.manager}</td>
      <td class="deal-amount">${formatCurrency(deal.amount)}</td>
      <td><span class="stage-badge ${deal.stage}">${getStageLabel(deal.stage)}</span></td>
      <td>
        <div class="probability-bar">
          <div class="probability-fill" style="width: ${deal.probability}%"></div>
        </div>
        <span style="margin-left: 8px; font-size: 12px;">${deal.probability}%</span>
      </td>
      <td>
        <div class="health-indicators">
          ${deal.health_positive.map(h => `<div class="health-indicator positive">✓ ${h}</div>`).join('')}
          ${deal.health_negative.map(h => `<div class="health-indicator negative">✗ ${h}</div>`).join('')}
        </div>
      </td>
      <td>${deal.last_call}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Calls Module
function renderCallsHistory() {
  const container = document.getElementById('callsHistory');
  container.innerHTML = '';
  
  mockData.calls_data.forEach(call => {
    const item = document.createElement('div');
    item.className = 'call-history-item';
    item.innerHTML = `
      <div class="call-history-header">
        <div class="call-history-title">📞 ${call.filename}</div>
        <div class="call-history-score">${call.quality_score}/20</div>
      </div>
      <div class="call-history-details">
        <span><strong>Менеджер:</strong> ${call.manager}</span>
        <span><strong>Клиент:</strong> ${call.client}</span>
        <span><strong>Длительность:</strong> ${call.duration}</span>
        <span><strong>Дата:</strong> ${call.date}</span>
      </div>
    `;
    item.addEventListener('click', () => displayCallAnalysis(call));
    container.appendChild(item);
  });
}

function setupCallUpload() {
  const uploadArea = document.getElementById('uploadArea');
  const fileInput = document.getElementById('audioFileInput');
  const selectBtn = document.getElementById('selectFileBtn');
  
  selectBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });
  
  uploadArea.addEventListener('click', () => {
    fileInput.click();
  });
  
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      simulateTranscription(e.target.files[0]);
    }
  });
}

function simulateTranscription(file) {
  const progressDiv = document.getElementById('transcriptionProgress');
  const progressBar = document.getElementById('transcriptionProgressBar');
  const statusText = document.getElementById('transcriptionStatus');
  
  progressDiv.style.display = 'block';
  document.getElementById('callAnalysisResults').style.display = 'none';
  
  const steps = [
    { progress: 20, text: 'Загрузка файла...' },
    { progress: 40, text: 'Обработка аудио...' },
    { progress: 60, text: 'Распознавание речи...' },
    { progress: 80, text: 'Анализ качества звонка...' },
    { progress: 100, text: 'Готово!' }
  ];
  
  let currentStep = 0;
  
  const interval = setInterval(() => {
    if (currentStep < steps.length) {
      progressBar.style.width = steps[currentStep].progress + '%';
      statusText.textContent = steps[currentStep].text;
      currentStep++;
    } else {
      clearInterval(interval);
      setTimeout(() => {
        progressDiv.style.display = 'none';
        // Use first call as example
        displayCallAnalysis(mockData.calls_data[0]);
      }, 500);
    }
  }, 800);
}

function displayCallAnalysis(call) {
  document.getElementById('callAnalysisResults').style.display = 'block';
  
  // Call info
  document.getElementById('callManager').textContent = call.manager;
  document.getElementById('callClient').textContent = call.client;
  document.getElementById('callDuration').textContent = call.duration;
  document.getElementById('callDate').textContent = call.date;
  
  // Quality score
  document.getElementById('qualityScoreValue').textContent = call.quality_score;
  const scoreLabel = call.quality_score >= 16 ? 'Отлично' : call.quality_score >= 12 ? 'Хорошо' : 'Удовлетворительно';
  document.getElementById('qualityScoreLabel').textContent = scoreLabel;
  document.getElementById('qualityScoreLabel').style.color = call.quality_score >= 16 ? 'var(--color-success)' : call.quality_score >= 12 ? 'var(--color-warning)' : 'var(--color-error)';
  
  // Metrics
  document.getElementById('metricPoliteness').style.width = (call.scores.politeness / 5 * 100) + '%';
  document.getElementById('metricPolitenessValue').textContent = call.scores.politeness + '/5';
  
  document.getElementById('metricUnderstanding').style.width = (call.scores.understanding / 5 * 100) + '%';
  document.getElementById('metricUnderstandingValue').textContent = call.scores.understanding + '/5';
  
  document.getElementById('metricSolution').style.width = (call.scores.solution / 5 * 100) + '%';
  document.getElementById('metricSolutionValue').textContent = call.scores.solution + '/5';
  
  document.getElementById('metricClosing').style.width = (call.scores.closing / 5 * 100) + '%';
  document.getElementById('metricClosingValue').textContent = call.scores.closing + '/5';
  
  // Transcription
  const transcriptionBox = document.getElementById('transcriptionText');
  const lines = call.transcription.split('. ');
  transcriptionBox.innerHTML = lines.map(line => {
    if (line.includes('Менеджер:')) {
      return `<div class="transcription-line"><span class="speaker-label agent">Менеджер:</span> ${line.replace('Менеджер:', '')}</div>`;
    } else if (line.includes('Клиент:')) {
      return `<div class="transcription-line"><span class="speaker-label client">Клиент:</span> ${line.replace('Клиент:', '')}</div>`;
    }
    return `<div class="transcription-line">${line}</div>`;
  }).join('');
  
  // Sentiment
  const sentimentBadge = document.getElementById('sentimentBadge');
  const sentimentLabels = { positive: 'Позитивный', neutral: 'Нейтральный', negative: 'Негативный' };
  sentimentBadge.textContent = sentimentLabels[call.sentiment];
  sentimentBadge.className = 'sentiment-badge ' + call.sentiment;
  
  // Key phrases
  const keyPhrases = document.getElementById('keyPhrases');
  keyPhrases.innerHTML = call.key_phrases.map(phrase => 
    `<span class="key-phrase">${phrase}</span>`
  ).join('');
  
  // Recommendations
  const recommendations = document.getElementById('recommendations');
  const recs = generateRecommendations(call);
  recommendations.innerHTML = recs.map(rec => `
    <div class="recommendation-item">
      <div class="recommendation-icon">${rec.icon}</div>
      <div class="recommendation-text">${rec.text}</div>
    </div>
  `).join('');
  
  // Scroll to results
  document.getElementById('callAnalysisResults').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function generateRecommendations(call) {
  const recs = [];
  
  if (call.scores.politeness < 5) {
    recs.push({ icon: '💬', text: 'Улучшите приветствие и используйте более вежливые формулировки в начале разговора.' });
  }
  
  if (call.scores.understanding < 4) {
    recs.push({ icon: '🎯', text: 'Задавайте больше уточняющих вопросов для лучшего понимания потребностей клиента.' });
  }
  
  if (call.scores.solution < 4) {
    recs.push({ icon: '💡', text: 'Предлагайте конкретные решения с привязкой к проблемам клиента.' });
  }
  
  if (call.scores.closing < 4) {
    recs.push({ icon: '✅', text: 'Обязательно назначайте следующий шаг и конкретную дату следующего контакта.' });
  }
  
  if (call.sentiment === 'negative') {
    recs.push({ icon: '😊', text: 'Обратите внимание на тональность разговора - клиент был недоволен.' });
  }
  
  if (recs.length === 0) {
    recs.push({ icon: '🌟', text: 'Отличный звонок! Продолжайте в том же духе.' });
  }
  
  return recs;
}

// Pulse Module
function renderPulseGrid() {
  const grid = document.getElementById('pulseGrid');
  grid.innerHTML = '';
  
  let deals = mockData.deals;
  if (currentManager !== 'all') {
    const manager = mockData.managers.find(m => m.id === parseInt(currentManager));
    if (manager) {
      deals = deals.filter(d => d.manager === manager.name);
    }
  }
  
  deals.forEach(deal => {
    const healthClass = getHealthClass(deal.probability);
    const card = document.createElement('div');
    card.className = 'pulse-card ' + healthClass;
    
    const recommendations = [];
    if (deal.health_negative.length > 0) {
      recommendations.push('Срочно связаться с клиентом');
      recommendations.push('Обновить информацию в CRM');
    }
    if (deal.probability < 50) {
      recommendations.push('Провести дополнительную презентацию');
    }
    if (recommendations.length === 0) {
      recommendations.push('Продолжить работу по плану');
    }
    
    card.innerHTML = `
      <div class="pulse-header">
        <div class="pulse-info">
          <h4>${deal.title}</h4>
          <p class="text-secondary">${deal.manager}</p>
        </div>
        <div class="pulse-score ${healthClass}">${deal.probability}</div>
      </div>
      <div class="pulse-details">
        <div class="pulse-detail">
          <span class="text-secondary">Сумма</span>
          <span class="deal-amount">${formatCurrency(deal.amount)}</span>
        </div>
        <div class="pulse-detail">
          <span class="text-secondary">Этап</span>
          <span>${getStageLabel(deal.stage)}</span>
        </div>
        <div class="pulse-detail">
          <span class="text-secondary">Вероятность</span>
          <span>${deal.probability}%</span>
        </div>
        <div class="pulse-detail">
          <span class="text-secondary">Последний контакт</span>
          <span>${deal.last_call}</span>
        </div>
      </div>
      <div class="pulse-recommendations">
        <strong>План действий:</strong>
        <ul>
          ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
        </ul>
      </div>
    `;
    grid.appendChild(card);
  });
}

// Assistant Module
function setupAssistant() {
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSendBtn');
  const quickActionBtns = document.querySelectorAll('.chat-quick-actions button');
  
  sendBtn.addEventListener('click', () => {
    const message = chatInput.value.trim();
    if (message) {
      sendChatMessage(message);
      chatInput.value = '';
    }
  });
  
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });
  
  quickActionBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      sendChatMessage(action);
    });
  });
}

function sendChatMessage(message) {
  const messagesContainer = document.getElementById('chatMessages');
  
  // Add user message
  const userMsg = document.createElement('div');
  userMsg.className = 'chat-message chat-message--user';
  userMsg.innerHTML = `
    <div class="chat-message-avatar">👤</div>
    <div class="chat-message-content">
      <p>${message}</p>
      <div class="chat-message-time">Сейчас</div>
    </div>
  `;
  messagesContainer.appendChild(userMsg);
  
  // Simulate AI response
  setTimeout(() => {
    const response = generateAIResponse(message);
    const aiMsg = document.createElement('div');
    aiMsg.className = 'chat-message chat-message--assistant';
    aiMsg.innerHTML = `
      <div class="chat-message-avatar">🤖</div>
      <div class="chat-message-content">
        <p>${response}</p>
        <div class="chat-message-time">Сейчас</div>
      </div>
    `;
    messagesContainer.appendChild(aiMsg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }, 1000);
  
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function generateAIResponse(message) {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes('анализ') || lowerMessage.includes('сделк')) {
    return `📊 <strong>Анализ последних 5 сделок:</strong><br><br>
    • Средняя вероятность: 60%<br>
    • Общая сумма: ${formatCurrency(mockData.deals.slice(0, 5).reduce((sum, d) => sum + d.amount, 0))}<br>
    • 2 сделки требуют срочного внимания<br>
    • Рекомендую связаться с клиентами по сделкам №2 и №4`;
  }
  
  if (lowerMessage.includes('кп') || lowerMessage.includes('предложени')) {
    return `📄 <strong>Коммерческое предложение сгенерировано:</strong><br><br>
    Уважаемый клиент!<br><br>
    Представляем вашему вниманию RUBI Chat Pro - инновационную платформу для управления отделом продаж с AI-анализом звонков.<br><br>
    <strong>Ключевые преимущества:</strong><br>
    • Автоматизация контроля воронки продаж<br>
    • Транскрибация и анализ качества звонков<br>
    • AI-рекомендации для каждой сделки<br>
    • Экономия 80% времени РОПа<br><br>
    Стоимость: от 49 000 ₽/мес`;
  }
  
  if (lowerMessage.includes('рекомендаци') || lowerMessage.includes('холодн')) {
    return `💡 <strong>Рекомендации по холодным лидам:</strong><br><br>
    1. Сделка №4 (ООО МегаБизнес) - не было контакта 15 дней. Срочно позвонить!<br>
    2. Сделка №2 (ЗАО Промторг) - низкая активность. Предложить встречу.<br>
    3. Используйте модуль "Оценка звонков" для анализа предыдущих разговоров<br>
    4. Обновите данные в CRM по всем холодным сделкам`;
  }
  
  if (lowerMessage.includes('письмо') || lowerMessage.includes('email')) {
    return `✉️ <strong>Шаблон письма клиенту:</strong><br><br>
    Тема: Предложение по оптимизации продаж<br><br>
    Добрый день, [Имя]!<br><br>
    Благодарю за уделенное время в нашем недавнем разговоре. Как и обещал, направляю детальную информацию о RUBI Chat Pro.<br><br>
    Наше решение поможет вам:<br>
    • Увеличить выполнение плана на 25-40%<br>
    • Сократить время на рутинные задачи в 5 раз<br>
    • Получить полную прозрачность работы отдела<br><br>
    Готов ответить на любые вопросы.<br><br>
    С уважением,<br>
    [Ваше имя]`;
  }
  
  return `Понял ваш запрос. Я могу помочь с:<br>
  • Анализом сделок и показателей<br>
  • Генерацией КП и писем<br>
  • Рекомендациями по работе с клиентами<br>
  • Оценкой эффективности менеджеров<br><br>
  Просто выберите действие из быстрых команд или задайте вопрос.`;
}

// Filters
function setupFilters() {
  document.getElementById('periodFilter').addEventListener('change', (e) => {
    currentPeriod = e.target.value;
    loadModuleData(currentModule);
  });
  
  document.getElementById('managerFilter').addEventListener('change', (e) => {
    currentManager = e.target.value;
    loadModuleData(currentModule);
  });
  
  document.getElementById('updateDataBtn').addEventListener('click', () => {
    loadModuleData(currentModule);
    alert('Данные обновлены!');
  });
}

// Initialize App
function initializeApp() {
  // Setup navigation
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      switchModule(item.dataset.module);
    });
  });
  
  // Setup filters
  setupFilters();
  
  // Setup modules
  setupCallUpload();
  setupAssistant();
  
  // Load initial module
  loadModuleData('dashboard');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Login form
  document.getElementById('loginForm').addEventListener('submit', handleLogin);
  document.getElementById('logoutBtn').addEventListener('click', handleLogout);
});