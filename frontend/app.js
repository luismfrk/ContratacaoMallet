const form = document.getElementById("dfd-form");
const tipoSelect = document.getElementById("tipo");
const contratadaFields = document.getElementById("contratada-fields");
const statusBox = document.getElementById("status");
const submitButton = document.getElementById("submit-button");
const previewSection = document.getElementById("preview-section");
const resultadoBox = document.getElementById("resultado");
const previewMode = document.getElementById("preview-mode");
const downloadButton = document.getElementById("download-button");
const dfdModule = document.getElementById("dfd-module");
const etpModule = document.getElementById("etp-module");
const showDfd = document.getElementById("show-dfd");
const showEtp = document.getElementById("show-etp");
const etpForm = document.getElementById("etp-form");
const etpItems = document.getElementById("etp-items");
const addEtpItem = document.getElementById("add-etp-item");
const etpStatus = document.getElementById("etp-status");
const etpSubmit = document.getElementById("etp-submit");
const etpPreview = document.getElementById("etp-preview");
const etpResult = document.getElementById("etp-result");
const etpDownload = document.getElementById("etp-download");
const showEtpCompras = document.getElementById("show-etp-compras");
const showEtpObras = document.getElementById("show-etp-obras");
const etpObrasForm = document.getElementById("etp-obras-form");
const etpObrasStatus = document.getElementById("etp-obras-status");
const etpObrasSubmit = document.getElementById("etp-obras-submit");
const etpObrasPreview = document.getElementById("etp-obras-preview");
const etpObrasResult = document.getElementById("etp-obras-result");
const etpObrasDownload = document.getElementById("etp-obras-download");
const showTr = document.getElementById("show-tr");
const trModule = document.getElementById("tr-module");
const showRequisicao = document.getElementById("show-requisicao");
const requisicaoModule = document.getElementById("requisicao-module");
const requisicaoForm = document.getElementById("requisicao-form");
const requisicaoArquivo = document.getElementById("requisicao-arquivo");
const requisicaoItens = document.getElementById("requisicao-itens");
const requisicaoResumo = document.getElementById("requisicao-resumo");
const requisicaoStatus = document.getElementById("requisicao-status");
const requisicaoDownload = document.getElementById("requisicao-download");
const trForm = document.getElementById("tr-form");
const trTipo = document.getElementById("tr-tipo");
const trFornecedor = document.getElementById("tr-fornecedor");
const trItemsFieldset = document.getElementById("tr-items-fieldset");
const trItems = document.getElementById("tr-items");
const addTrItem = document.getElementById("add-tr-item");
const trStatus = document.getElementById("tr-status");
const trSubmit = document.getElementById("tr-submit");
const trPreview = document.getElementById("tr-preview");
const trResult = document.getElementById("tr-result");
const trDownload = document.getElementById("tr-download");
const currentContract = document.getElementById("current-contract");
const currentSecretariat = document.getElementById("current-secretariat");
const newContractTitle = document.getElementById("new-contract-title");
const newContractObject = document.getElementById("new-contract-object");
const createContract = document.getElementById("create-contract");
const documentHistory = document.getElementById("document-history");
const workspaceStatus = document.getElementById("workspace-status");
const saveDfd = document.getElementById("save-dfd");
const saveEtp = document.getElementById("save-etp");
const saveEtpObras = document.getElementById("save-etp-obras");
const saveTr = document.getElementById("save-tr");
const authOverlay = document.getElementById("auth-overlay");
const authForm = document.getElementById("auth-form");
const authTitle = document.getElementById("auth-title");
const authDescription = document.getElementById("auth-description");
const authNameField = document.getElementById("auth-name-field");
const authName = document.getElementById("auth-name");
const authLogin = document.getElementById("auth-login");
const authPassword = document.getElementById("auth-password");
const authConfirmField = document.getElementById("auth-confirm-field");
const authConfirmPassword = document.getElementById("auth-confirm-password");
const authPasswordHelp = document.getElementById("auth-password-help");
const authStatus = document.getElementById("auth-status");
const authSubmit = document.getElementById("auth-submit");
const currentUserName = document.getElementById("current-user-name");
const userChip = document.getElementById("user-chip");
const logoutButton = document.getElementById("logout-button");
const manageUsers = document.getElementById("manage-users");
const usersOverlay = document.getElementById("users-overlay");
const closeUsers = document.getElementById("close-users");
const usersList = document.getElementById("users-list");
const userForm = document.getElementById("user-form");
const newUserName = document.getElementById("new-user-name");
const newUserLogin = document.getElementById("new-user-login");
const newUserPassword = document.getElementById("new-user-password");
const newUserRole = document.getElementById("new-user-role");
const newUserSecretariat = document.getElementById("new-user-secretariat");
const editUserId = document.getElementById("edit-user-id");
const editUserActive = document.getElementById("edit-user-active");
const editUserPassword = document.getElementById("edit-user-password");
const saveUserButton = document.getElementById("save-user-button");
const cancelUserEdit = document.getElementById("cancel-user-edit");
const userStatus = document.getElementById("user-status");
const loginTab = document.getElementById("login-tab");
const registerTab = document.getElementById("register-tab");

let tiposDFD = [];
let ultimaSolicitacao = null;
let ultimoETP = null;
let ultimoETPObras = null;
let tiposTR = [];
let ultimoTR = null;
let itensRequisicao = [];
let gruposRequisicao = {};
let metadadosRequisicao = {};
let modoAcesso = "login";
let primeiroUsuarioPendente = false;
let usuarioAtual = null;
let moduloAtual = null;
let contratacoesDisponiveis = [];

const fetchOriginal = window.fetch.bind(window);
window.fetch = async (input, options) => {
  const response = await fetchOriginal(input, options);
  const endereco = typeof input === "string" ? input : input.url;
  const rotaAutenticacao = endereco.includes("/api/auth/");
  if (response.status === 401 && !rotaAutenticacao) {
    usuarioAtual = null;
    userChip.classList.add("hidden");
    logoutButton.classList.add("hidden");
    manageUsers.classList.add("hidden");
    configurarTelaAcesso(false);
    authStatus.textContent = "Sua sessão expirou. Entre novamente.";
    authStatus.className = "status error";
  }
  return response;
};

newUserRole.addEventListener("change", () => {
  const administrador = newUserRole.value === "admin";
  newUserSecretariat.disabled = administrador;
  newUserSecretariat.required = !administrador;
  if (administrador) newUserSecretariat.value = "";
});

function mostrarModulo(nome) {
  moduloAtual = nome;
  dfdModule.classList.toggle("hidden", nome !== "dfd");
  etpModule.classList.toggle("hidden", nome !== "etp");
  trModule.classList.toggle("hidden", nome !== "tr");
  requisicaoModule.classList.toggle("hidden", nome !== "requisicao");
  showDfd.classList.toggle("active", nome === "dfd");
  showEtp.classList.toggle("active", nome === "etp");
  showTr.classList.toggle("active", nome === "tr");
  showRequisicao.classList.toggle("active", nome === "requisicao");
}

function alternarModulo(nome) {
  if (nome === "requisicao" && currentSecretariat.value) {
    document.getElementById("requisicao-destino").value = `SECRETARIA MUNICIPAL DE ${currentSecretariat.value.toUpperCase()}`;
    document.getElementById("requisicao-fonte").value = currentSecretariat.value === "Educação"
      ? "1000/ 1104 / 3104 / 1103"
      : "";
  }
  mostrarModulo(moduloAtual === nome ? null : nome);
}

showDfd.addEventListener("click", () => alternarModulo("dfd"));
showEtp.addEventListener("click", () => alternarModulo("etp"));
showTr.addEventListener("click", () => alternarModulo("tr"));
showRequisicao.addEventListener("click", () => alternarModulo("requisicao"));

function mostrarTipoETP(tipo) {
  const compras = tipo === "compras";
  etpForm.classList.toggle("hidden", !compras);
  etpPreview.classList.toggle("hidden", !compras || !ultimoETP);
  etpObrasForm.classList.toggle("hidden", compras);
  etpObrasPreview.classList.toggle("hidden", compras || !ultimoETPObras);
  showEtpCompras.classList.toggle("active", compras);
  showEtpObras.classList.toggle("active", !compras);
}

showEtpCompras.addEventListener("click", () => mostrarTipoETP("compras"));
showEtpObras.addEventListener("click", () => mostrarTipoETP("obras"));

function configurarCamposContratada() {
  const tipo = tiposDFD.find((item) => item.id === tipoSelect.value);
  const obrigatorio = Boolean(tipo?.exige_contratada);
  contratadaFields.classList.toggle("hidden", !obrigatorio);
  contratadaFields.querySelectorAll("input").forEach((input) => {
    input.required = obrigatorio;
  });
}

async function carregarTipos() {
  try {
    const response = await fetch("/api/dfd/tipos");
    if (!response.ok) throw new Error("Não foi possível carregar os tipos de DFD.");
    const payload = await response.json();
    tiposDFD = payload.tipos;
    tipoSelect.innerHTML =
      '<option value="">Selecione...</option>' +
      tiposDFD
        .map((tipo) => `<option value="${tipo.id}">${tipo.titulo} — ${tipo.anexo}</option>`)
        .join("");
  } catch (error) {
    tipoSelect.innerHTML = '<option value="">Tipos indisponíveis</option>';
    statusBox.textContent = error.message;
    statusBox.className = "status error";
  }
}

tipoSelect.addEventListener("change", configurarCamposContratada);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  statusBox.textContent = "Gerando a prévia...";
  statusBox.className = "status";
  submitButton.disabled = true;
  previewSection.classList.add("hidden");

  const formData = new FormData(form);
  const tipo = formData.get("tipo");
  const dados = Object.fromEntries(formData.entries());
  delete dados.tipo;
  ultimaSolicitacao = { tipo, dados };

  try {
    const response = await fetch("/api/dfd/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo, dados }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível gerar o DFD.");

    resultadoBox.textContent = payload.resultado.conteudo;
    previewMode.textContent = payload.resultado.modo;
    previewSection.classList.remove("hidden");
    statusBox.textContent =
      "Prévia gerada. Revise todas as informações antes de utilizar o documento.";
    statusBox.className = "status success";
    previewSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    statusBox.textContent = error.message || "Erro de comunicação com o servidor.";
    statusBox.className = "status error";
  } finally {
    submitButton.disabled = false;
  }
});

downloadButton.addEventListener("click", async () => {
  if (!ultimaSolicitacao) return;
  downloadButton.disabled = true;
  statusBox.textContent = "Preparando o arquivo Word...";
  statusBox.className = "status";

  try {
    const response = await fetch("/api/dfd/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimaSolicitacao),
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Não foi possível gerar o arquivo Word.");
    }

    const arquivo = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const correspondencia = disposition.match(/filename="([^"]+)"/);
    const nomeArquivo = correspondencia?.[1] || "DFD.docx";
    const url = URL.createObjectURL(arquivo);
    const link = document.createElement("a");
    link.href = url;
    link.download = nomeArquivo;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    statusBox.textContent = "Arquivo Word gerado e baixado com sucesso.";
    statusBox.className = "status success";
  } catch (error) {
    statusBox.textContent = error.message || "Erro de comunicação com o servidor.";
    statusBox.className = "status error";
  } finally {
    downloadButton.disabled = false;
  }
});

function adicionarItemETP(dado = {}) {
  const linha = document.createElement("div");
  linha.className = "item-row";
  linha.innerHTML = `
    <label>Descrição <span>*</span>
      <input class="item-description" required />
    </label>
    <label>Quantidade <span>*</span>
      <input class="item-quantity" required placeholder="Ex.: 500 unidades" />
    </label>
    <button class="remove-item" type="button" title="Remover item">×</button>
  `;
  linha.querySelector(".remove-item").addEventListener("click", () => {
    if (etpItems.children.length > 1) linha.remove();
  });
  linha.querySelector(".item-description").value = dado.descricao || "";
  linha.querySelector(".item-quantity").value = dado.quantidade || "";
  etpItems.appendChild(linha);
}

function dadosETP() {
  const formData = new FormData(etpForm);
  const dados = Object.fromEntries(formData.entries());
  dados.itens = [...etpItems.querySelectorAll(".item-row")].map((linha) => ({
    descricao: linha.querySelector(".item-description").value,
    quantidade: linha.querySelector(".item-quantity").value,
  }));
  return dados;
}

addEtpItem.addEventListener("click", adicionarItemETP);
adicionarItemETP();

etpForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!etpForm.reportValidity()) return;

  ultimoETP = { dados: dadosETP() };
  etpStatus.textContent = "Gerando a prévia...";
  etpStatus.className = "status";
  etpSubmit.disabled = true;
  etpPreview.classList.add("hidden");

  try {
    const response = await fetch("/api/etp/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoETP),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível gerar o ETP.");
    etpResult.textContent = payload.resultado.conteudo;
    etpPreview.classList.remove("hidden");
    etpStatus.textContent = "Prévia gerada. Revise os dados antes de baixar o Word.";
    etpStatus.className = "status success";
    etpPreview.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    etpStatus.textContent = error.message || "Erro de comunicação com o servidor.";
    etpStatus.className = "status error";
  } finally {
    etpSubmit.disabled = false;
  }
});

etpDownload.addEventListener("click", async () => {
  if (!ultimoETP) return;
  etpDownload.disabled = true;
  etpStatus.textContent = "Preparando o ETP em Word...";
  try {
    const response = await fetch("/api/etp/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoETP),
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Não foi possível gerar o arquivo Word.");
    }
    const arquivo = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const nome = disposition.match(/filename="([^"]+)"/)?.[1] || "ETP.docx";
    const url = URL.createObjectURL(arquivo);
    const link = document.createElement("a");
    link.href = url;
    link.download = nome;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    etpStatus.textContent = "ETP em Word gerado com sucesso.";
    etpStatus.className = "status success";
  } catch (error) {
    etpStatus.textContent = error.message || "Erro de comunicação com o servidor.";
    etpStatus.className = "status error";
  } finally {
    etpDownload.disabled = false;
  }
});

etpObrasForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!etpObrasForm.reportValidity()) return;
  ultimoETPObras = {
    dados: Object.fromEntries(new FormData(etpObrasForm).entries()),
  };
  etpObrasStatus.textContent = "Gerando a prévia...";
  etpObrasStatus.className = "status";
  etpObrasSubmit.disabled = true;
  etpObrasPreview.classList.add("hidden");
  try {
    const response = await fetch("/api/etp/obras/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoETPObras),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível gerar o ETP.");
    etpObrasResult.textContent = payload.resultado.conteudo;
    etpObrasPreview.classList.remove("hidden");
    etpObrasStatus.textContent = "Prévia gerada. Revise os dados antes de baixar.";
    etpObrasStatus.className = "status success";
    etpObrasPreview.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    etpObrasStatus.textContent = error.message || "Erro de comunicação com o servidor.";
    etpObrasStatus.className = "status error";
  } finally {
    etpObrasSubmit.disabled = false;
  }
});

etpObrasDownload.addEventListener("click", async () => {
  if (!ultimoETPObras) return;
  etpObrasDownload.disabled = true;
  etpObrasStatus.textContent = "Preparando o arquivo Word...";
  try {
    const response = await fetch("/api/etp/obras/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoETPObras),
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Não foi possível gerar o Word.");
    }
    const arquivo = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const nome = disposition.match(/filename="([^"]+)"/)?.[1] || "ETP_obras.docx";
    const url = URL.createObjectURL(arquivo);
    const link = document.createElement("a");
    link.href = url;
    link.download = nome;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    etpObrasStatus.textContent = "ETP de obras gerado com sucesso.";
    etpObrasStatus.className = "status success";
  } catch (error) {
    etpObrasStatus.textContent = error.message || "Erro de comunicação com o servidor.";
    etpObrasStatus.className = "status error";
  } finally {
    etpObrasDownload.disabled = false;
  }
});

async function carregarTiposTR() {
  try {
    const response = await fetch("/api/tr/tipos");
    if (!response.ok) throw new Error("Não foi possível carregar os tipos de TR.");
    tiposTR = (await response.json()).tipos;
    trTipo.innerHTML =
      '<option value="">Selecione...</option>' +
      tiposTR.map((tipo) => `<option value="${tipo.id}">${tipo.titulo}</option>`).join("");
  } catch (error) {
    trTipo.innerHTML = '<option value="">Tipos indisponíveis</option>';
    trStatus.textContent = error.message;
    trStatus.className = "status error";
  }
}

function configurarTR() {
  const config = tiposTR.find((tipo) => tipo.id === trTipo.value);
  const fornecedor = Boolean(config?.exige_fornecedor);
  const itens = Boolean(config?.exige_itens);
  trFornecedor.classList.toggle("hidden", !fornecedor);
  trFornecedor.querySelectorAll("input, textarea").forEach((campo) => {
    campo.required = fornecedor;
  });
  trItemsFieldset.classList.toggle("hidden", !itens);
  trItemsFieldset.querySelectorAll(".tr-description, .tr-quantity, .tr-unit-price")
    .forEach((campo) => {
      campo.required = itens;
    });
}

function adicionarItemTR(dado = {}) {
  const linha = document.createElement("div");
  linha.className = "tr-item-row";
  linha.innerHTML = `
    <label>Descrição <span>*</span><input class="tr-description" required /></label>
    <label>Código<input class="tr-code" /></label>
    <label>Qtd. <span>*</span><input class="tr-quantity" type="number" min="0.01" step="0.01" required /></label>
    <label>Valor unit. <span>*</span><input class="tr-unit-price" type="number" min="0" step="0.01" required /></label>
    <button class="remove-item" type="button" title="Remover item">×</button>
  `;
  linha.querySelector(".remove-item").addEventListener("click", () => {
    if (trItems.children.length > 1) linha.remove();
  });
  linha.querySelector(".tr-description").value = dado.descricao || "";
  linha.querySelector(".tr-code").value = dado.codigo || "";
  linha.querySelector(".tr-quantity").value = dado.quantidade || "";
  linha.querySelector(".tr-unit-price").value = dado.valor_unitario || "";
  trItems.appendChild(linha);
}

function solicitacaoTR() {
  const formData = new FormData(trForm);
  const tipo = formData.get("tipo");
  const dados = Object.fromEntries(formData.entries());
  delete dados.tipo;
  dados.itens = [...trItems.querySelectorAll(".tr-item-row")].map((linha) => ({
    descricao: linha.querySelector(".tr-description").value,
    codigo: linha.querySelector(".tr-code").value,
    quantidade: linha.querySelector(".tr-quantity").value,
    valor_unitario: linha.querySelector(".tr-unit-price").value,
  }));
  return { tipo, dados };
}

trTipo.addEventListener("change", configurarTR);
addTrItem.addEventListener("click", adicionarItemTR);
adicionarItemTR();

trForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!trForm.reportValidity()) return;
  ultimoTR = solicitacaoTR();
  trStatus.textContent = "Gerando a prévia...";
  trStatus.className = "status";
  trSubmit.disabled = true;
  trPreview.classList.add("hidden");
  try {
    const response = await fetch("/api/tr/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoTR),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível gerar o TR.");
    trResult.textContent = payload.resultado.conteudo;
    trPreview.classList.remove("hidden");
    trStatus.textContent = "Prévia gerada. Revise os dados antes de baixar.";
    trStatus.className = "status success";
    trPreview.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    trStatus.textContent = error.message || "Erro de comunicação com o servidor.";
    trStatus.className = "status error";
  } finally {
    trSubmit.disabled = false;
  }
});

trDownload.addEventListener("click", async () => {
  if (!ultimoTR) return;
  trDownload.disabled = true;
  trStatus.textContent = "Preparando o TR em Word...";
  try {
    const response = await fetch("/api/tr/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ultimoTR),
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Não foi possível gerar o Word.");
    }
    const arquivo = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const nome = disposition.match(/filename="([^"]+)"/)?.[1] || "TR.docx";
    const url = URL.createObjectURL(arquivo);
    const link = document.createElement("a");
    link.href = url;
    link.download = nome;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    trStatus.textContent = "Termo de Referência gerado com sucesso.";
    trStatus.className = "status success";
  } catch (error) {
    trStatus.textContent = error.message || "Erro de comunicação com o servidor.";
    trStatus.className = "status error";
  } finally {
    trDownload.disabled = false;
  }
});

function preencherFormulario(formulario, dados) {
  Object.entries(dados).forEach(([nome, valor]) => {
    if (nome === "itens") return;
    const campo = formulario.elements.namedItem(nome);
    if (campo && typeof valor !== "object") campo.value = valor ?? "";
  });
}

async function carregarContratacoes(selecionarId = null) {
  try {
    const response = await fetch("/api/contratacoes");
    if (!response.ok) throw new Error("Não foi possível carregar as contratações.");
    contratacoesDisponiveis = (await response.json()).contratacoes;
    atualizarContratacoesDaSecretaria(selecionarId);
  } catch (error) {
    workspaceStatus.textContent = error.message;
    workspaceStatus.className = "status error";
  }
}

function atualizarContratacoesDaSecretaria(selecionarId = null) {
    const secretaria = currentSecretariat.value;
    const valorAtual = selecionarId || currentContract.value;
    currentContract.innerHTML =
      '<option value="">Selecione ou crie uma contratação</option>' +
      contratacoesDisponiveis
        .filter((item) => !secretaria || item.secretaria === secretaria || item.secretaria === `Secretaria Municipal de ${secretaria}`)
        .map((item) => `<option value="${item.id}">${item.titulo}</option>`)
        .join("");
    if (valorAtual) currentContract.value = String(valorAtual);
    if (currentContract.value) carregarHistorico();
    else documentHistory.textContent = secretaria ? "Selecione ou crie uma contratação para consultar o histórico." : "Selecione uma secretaria.";
}

async function carregarHistorico() {
  const contratacaoId = currentContract.value;
  if (!contratacaoId) {
    documentHistory.textContent = "Selecione uma contratação para consultar o histórico.";
    return;
  }
  try {
    const response = await fetch(`/api/contratacoes/${contratacaoId}/documentos`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Erro ao carregar histórico.");
    if (!payload.documentos.length) {
      documentHistory.textContent = "Nenhum rascunho salvo.";
      return;
    }
    documentHistory.innerHTML = "";
    payload.documentos.forEach((documento) => {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = "history-button";
      const icone = document.createElement("span");
      icone.className = "ion-icon icon-time";
      icone.setAttribute("aria-hidden", "true");
      const rotulo = document.createElement("span");
      rotulo.textContent =
        `${documento.tipo.toUpperCase()} · ${documento.subtipo} · v${documento.versao}` +
        ` · ${documento.criado_por || "registro anterior"}`;
      botao.append(icone, rotulo);
      botao.addEventListener("click", () => carregarDocumento(documento.id));
      documentHistory.appendChild(botao);
    });
  } catch (error) {
    workspaceStatus.textContent = error.message;
    workspaceStatus.className = "status error";
  }
}

async function carregarDocumento(documentoId) {
  try {
    const response = await fetch(`/api/documentos/${documentoId}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Documento não encontrado.");
    const documento = payload.documento;
    if (documento.tipo === "dfd") {
      mostrarModulo("dfd");
      ultimaSolicitacao = null;
      previewSection.classList.add("hidden");
      tipoSelect.value = documento.subtipo;
      configurarCamposContratada();
      preencherFormulario(form, documento.dados);
    } else if (documento.tipo === "etp" && documento.subtipo === "compras_servicos") {
      mostrarModulo("etp");
      ultimoETP = null;
      etpPreview.classList.add("hidden");
      mostrarTipoETP("compras");
      preencherFormulario(etpForm, documento.dados);
      etpItems.innerHTML = "";
      (documento.dados.itens || [{}]).forEach(adicionarItemETP);
    } else if (documento.tipo === "etp") {
      mostrarModulo("etp");
      ultimoETPObras = null;
      etpObrasPreview.classList.add("hidden");
      mostrarTipoETP("obras");
      preencherFormulario(etpObrasForm, documento.dados);
    } else if (documento.tipo === "tr") {
      mostrarModulo("tr");
      ultimoTR = null;
      trPreview.classList.add("hidden");
      trTipo.value = documento.subtipo;
      configurarTR();
      preencherFormulario(trForm, documento.dados);
      trItems.innerHTML = "";
      (documento.dados.itens || [{}]).forEach(adicionarItemTR);
      configurarTR();
    }
    workspaceStatus.textContent =
      `${documento.tipo.toUpperCase()} versão ${documento.versao} carregado` +
      ` (${documento.criado_por || "registro anterior"}).`;
    workspaceStatus.className = "status success";
  } catch (error) {
    workspaceStatus.textContent = error.message;
    workspaceStatus.className = "status error";
  }
}

async function salvarRascunho(tipo, subtipo, dados) {
  const contratacaoId = currentContract.value;
  if (!contratacaoId) {
    workspaceStatus.textContent = "Selecione ou crie uma contratação antes de salvar.";
    workspaceStatus.className = "status error";
    return;
  }
  if (!subtipo) {
    workspaceStatus.textContent = "Selecione o tipo do documento antes de salvar.";
    workspaceStatus.className = "status error";
    return;
  }
  try {
    const response = await fetch(`/api/contratacoes/${contratacaoId}/documentos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo, subtipo, dados }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível salvar.");
    workspaceStatus.textContent =
      `${tipo.toUpperCase()} salvo como versão ${payload.documento.versao}.`;
    workspaceStatus.className = "status success";
    await carregarHistorico();
  } catch (error) {
    workspaceStatus.textContent = error.message;
    workspaceStatus.className = "status error";
  }
}

createContract.addEventListener("click", async () => {
  const titulo = newContractTitle.value.trim();
  const secretaria = currentSecretariat.value;
  if (!secretaria) {
    workspaceStatus.textContent = "Selecione a secretaria responsável.";
    workspaceStatus.className = "status error";
    return;
  }
  if (!titulo) {
    workspaceStatus.textContent = "Informe um título para a contratação.";
    workspaceStatus.className = "status error";
    return;
  }
  try {
    const response = await fetch("/api/contratacoes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        titulo,
        objeto: newContractObject.value,
        secretaria,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível criar.");
    newContractTitle.value = "";
    newContractObject.value = "";
    await carregarContratacoes(payload.contratacao.id);
    workspaceStatus.textContent = "Contratação criada e selecionada.";
    workspaceStatus.className = "status success";
  } catch (error) {
    workspaceStatus.textContent = error.message;
    workspaceStatus.className = "status error";
  }
});

currentContract.addEventListener("change", carregarHistorico);
currentSecretariat.addEventListener("change", () => {
  atualizarContratacoesDaSecretaria();
  const secretaria = currentSecretariat.value;
  document.querySelectorAll('[name="unidade_requisitante"]').forEach((campo) => {
    campo.value = secretaria ? `Secretaria Municipal de ${secretaria}` : "";
  });
  document.getElementById("requisicao-destino").value = secretaria
    ? `SECRETARIA MUNICIPAL DE ${secretaria.toUpperCase()}`
    : "";
  document.getElementById("requisicao-fonte").value = secretaria === "Educação"
    ? "1000/ 1104 / 3104 / 1103"
    : "";
});
saveDfd.addEventListener("click", () => {
  const dados = Object.fromEntries(new FormData(form).entries());
  const subtipo = dados.tipo;
  delete dados.tipo;
  salvarRascunho("dfd", subtipo, dados);
});
saveEtp.addEventListener("click", () =>
  salvarRascunho("etp", "compras_servicos", dadosETP())
);
saveEtpObras.addEventListener("click", () =>
  salvarRascunho(
    "etp",
    "obras_engenharia",
    Object.fromEntries(new FormData(etpObrasForm).entries())
  )
);
saveTr.addEventListener("click", () => {
  const solicitacao = solicitacaoTR();
  salvarRascunho("tr", solicitacao.tipo, solicitacao.dados);
});

function selecionarModoAutenticacao(modo) {
  modoAcesso = modo;
  const cadastro = modo === "register";
  loginTab.classList.toggle("active", !cadastro);
  registerTab.classList.toggle("active", cadastro);
  loginTab.setAttribute("aria-selected", String(!cadastro));
  registerTab.setAttribute("aria-selected", String(cadastro));
  authNameField.classList.toggle("hidden", !cadastro);
  authConfirmField.classList.toggle("hidden", !cadastro);
  authName.required = cadastro;
  authConfirmPassword.required = cadastro;
  authPasswordHelp.classList.toggle("hidden", !cadastro);
  authPassword.autocomplete = cadastro ? "new-password" : "current-password";
  authTitle.textContent = cadastro
    ? (primeiroUsuarioPendente ? "Criar conta administradora" : "Criar sua conta")
    : "Entrar no sistema";
  authDescription.textContent = cadastro
    ? (primeiroUsuarioPendente
      ? "Este é o primeiro acesso. A conta criada administrará os demais usuários."
      : "Cadastre-se para elaborar e salvar documentos com sua identificação.")
    : "Informe suas credenciais para continuar.";
  authSubmit.textContent = cadastro ? "Criar conta" : "Entrar";
  authStatus.textContent = "";
  authStatus.className = "status";
}

function configurarTelaAcesso(primeiroAcesso = false) {
  primeiroUsuarioPendente = primeiroAcesso;
  authOverlay.classList.remove("hidden");
  selecionarModoAutenticacao(primeiroAcesso ? "register" : "login");
}

async function ativarAplicacao(usuario) {
  usuarioAtual = usuario;
  mostrarModulo(null);
  authOverlay.classList.add("hidden");
  currentUserName.textContent = usuario.nome;
  userChip.classList.remove("hidden");
  logoutButton.classList.remove("hidden");
  manageUsers.classList.toggle("hidden", usuario.perfil !== "admin");
  await Promise.all([carregarTipos(), carregarTiposTR(), carregarContratacoes()]);
}

async function verificarAutenticacao() {
  try {
    const response = await fetch("/api/auth/status");
    const payload = await response.json();
    if (payload.setup_required) {
      configurarTelaAcesso(true);
    } else if (!payload.authenticated) {
      configurarTelaAcesso(false);
    } else {
      await ativarAplicacao(payload.user);
    }
  } catch {
    configurarTelaAcesso(false);
    authStatus.textContent = "Não foi possível comunicar com o servidor.";
    authStatus.className = "status error";
  }
}

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const cadastro = modoAcesso === "register";
  if (cadastro && authPassword.value !== authConfirmPassword.value) {
    authStatus.textContent = "As senhas informadas não são iguais.";
    authStatus.className = "status error";
    return;
  }
  authSubmit.disabled = true;
  authStatus.textContent = cadastro
    ? "Criando sua conta..."
    : "Verificando credenciais...";
  authStatus.className = "status";
  try {
    const endpoint = cadastro
      ? (primeiroUsuarioPendente ? "/api/auth/setup" : "/api/auth/register")
      : "/api/auth/login";
    const body = {
      login: authLogin.value,
      senha: authPassword.value,
    };
    if (cadastro) body.nome = authName.value;
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível entrar.");
    authForm.reset();
    await ativarAplicacao(payload.user);
  } catch (error) {
    authStatus.textContent = error.message;
    authStatus.className = "status error";
  } finally {
    authSubmit.disabled = false;
  }
});

loginTab.addEventListener("click", () => selecionarModoAutenticacao("login"));
registerTab.addEventListener("click", () => selecionarModoAutenticacao("register"));

logoutButton.addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" });
  usuarioAtual = null;
  userChip.classList.add("hidden");
  logoutButton.classList.add("hidden");
  manageUsers.classList.add("hidden");
  configurarTelaAcesso(false);
});

async function carregarUsuarios() {
  const response = await fetch("/api/usuarios");
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "Erro ao carregar usuários.");
  usersList.innerHTML = "";
  payload.usuarios.forEach((usuario) => {
    const item = document.createElement("div");
    item.className = "user-list-item";
    const nome = document.createElement("strong");
    nome.textContent = usuario.nome;
    const login = document.createElement("small");
    login.textContent = `@${usuario.login}${usuario.secretaria ? ` · ${usuario.secretaria}` : " · Todas as secretarias"}`;
    const perfil = document.createElement("span");
    perfil.className = "role-badge";
    perfil.textContent = usuario.perfil;
    item.append(nome, login, perfil);
    item.title = "Clique para editar";
    item.addEventListener("click", () => iniciarEdicaoUsuario(usuario));
    usersList.appendChild(item);
  });
}

function iniciarEdicaoUsuario(usuario) {
  editUserId.value = usuario.id;
  newUserName.value = usuario.nome;
  newUserLogin.value = usuario.login;
  newUserPassword.value = "";
  newUserPassword.required = false;
  newUserRole.value = usuario.perfil;
  newUserSecretariat.value = usuario.secretaria || "";
  newUserSecretariat.disabled = usuario.perfil === "admin";
  editUserActive.value = usuario.ativo ? "1" : "0";
  editUserPassword.value = "";
  document.querySelectorAll(".edit-only").forEach((elemento) => elemento.classList.remove("hidden"));
  cancelUserEdit.classList.remove("hidden");
  saveUserButton.lastChild.textContent = "Salvar alterações";
  userStatus.textContent = `Editando ${usuario.nome}`;
}

function encerrarEdicaoUsuario() {
  userForm.reset();
  editUserId.value = "";
  newUserPassword.required = true;
  newUserSecretariat.disabled = false;
  document.querySelectorAll(".edit-only").forEach((elemento) => elemento.classList.add("hidden"));
  cancelUserEdit.classList.add("hidden");
  saveUserButton.lastChild.textContent = "Cadastrar usuário";
}

cancelUserEdit.addEventListener("click", () => { encerrarEdicaoUsuario(); userStatus.textContent = ""; });

manageUsers.addEventListener("click", async () => {
  usersOverlay.classList.remove("hidden");
  userStatus.textContent = "";
  try {
    await carregarUsuarios();
  } catch (error) {
    userStatus.textContent = error.message;
    userStatus.className = "status error";
  }
});

closeUsers.addEventListener("click", () => usersOverlay.classList.add("hidden"));

userForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  userStatus.textContent = "Cadastrando usuário...";
  userStatus.className = "status";
  try {
    const editando = Boolean(editUserId.value);
    const corpo = editando ? {
      nome: newUserName.value, login: newUserLogin.value, perfil: newUserRole.value,
      secretaria: newUserRole.value === "admin" ? "" : newUserSecretariat.value,
      ativo: editUserActive.value === "1", senha: editUserPassword.value,
    } : {
      nome: newUserName.value, login: newUserLogin.value, senha: newUserPassword.value,
      perfil: newUserRole.value,
      secretaria: newUserRole.value === "admin" ? "" : newUserSecretariat.value,
    };
    const response = await fetch(editando ? `/api/usuarios/${editUserId.value}` : "/api/usuarios", {
      method: editando ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível cadastrar.");
    encerrarEdicaoUsuario();
    userStatus.textContent = editando ? "Usuário atualizado com sucesso." : "Usuário cadastrado com sucesso.";
    userStatus.className = "status success";
    await carregarUsuarios();
  } catch (error) {
    userStatus.textContent = error.message;
    userStatus.className = "status error";
  }
});

function desenharItensRequisicao() {
  requisicaoItens.innerHTML = "";
  itensRequisicao.forEach((item, indice) => {
    const linha = document.createElement("div");
    linha.className = "requisicao-item-row";
    linha.innerHTML = `
      <label>Descrição<input class="req-descricao" value="" required /></label>
      <label>Quantidade<input class="req-quantidade" type="number" min="0.01" step="0.01" required /></label>
      <label>Valor unitário<input class="req-valor" type="number" min="0" step="0.01" required /></label>
      <label>Desconto (%)<input class="req-desconto-item" type="number" min="0" max="100" step="0.01" /></label>`;
    linha.querySelector(".req-descricao").value = item.descricao;
    linha.querySelector(".req-quantidade").value = item.quantidade;
    linha.querySelector(".req-valor").value = item.valor_unitario;
    linha.querySelector(".req-desconto-item").value = item.desconto || 0;
    linha.querySelector(".req-descricao").addEventListener("input", (e) => itensRequisicao[indice].descricao = e.target.value);
    linha.querySelector(".req-quantidade").addEventListener("input", (e) => itensRequisicao[indice].quantidade = Number(e.target.value));
    linha.querySelector(".req-valor").addEventListener("input", (e) => itensRequisicao[indice].valor_unitario = Number(e.target.value));
    linha.querySelector(".req-desconto-item").addEventListener("input", (e) => itensRequisicao[indice].desconto = Number(e.target.value));
    requisicaoItens.appendChild(linha);
  });
}

document.getElementById("requisicao-importar").addEventListener("click", async () => {
  if (!requisicaoArquivo.files[0]) {
    requisicaoStatus.textContent = "Selecione a planilha do orçamento.";
    requisicaoStatus.className = "status error";
    return;
  }
  const dados = new FormData();
  dados.append("arquivo", requisicaoArquivo.files[0]);
  requisicaoStatus.textContent = "Lendo orçamento...";
  requisicaoStatus.className = "status";
  try {
    const response = await fetch("/api/requisicoes/importar", { method: "POST", body: dados });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Não foi possível ler o orçamento.");
    gruposRequisicao = payload.resultado.grupos || {};
    itensRequisicao = gruposRequisicao[payload.resultado.tipo]?.itens || payload.resultado.itens;
    const descontos = [...new Set(itensRequisicao.map((item) => Number(item.desconto || 0)))];
    if (descontos.length === 1) document.getElementById("requisicao-desconto").value = descontos[0];
    const metadados = payload.resultado.metadados || {};
    metadadosRequisicao = metadados;
    document.getElementById("requisicao-tipo").value = payload.resultado.tipo || "material";
    if (metadados.fornecedor) document.getElementById("requisicao-fornecedor").value = metadados.fornecedor;
    if (metadados.endereco) document.getElementById("requisicao-endereco").value = metadados.endereco;
    if (metadados.cidade) document.getElementById("requisicao-cidade").value = metadados.cidade;
    if (metadados.identificacao) document.getElementById("requisicao-identificacao").value = metadados.identificacao;
    desenharItensRequisicao();
    const total = payload.resultado.total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    if (payload.resultado.misto) {
      const materiais = gruposRequisicao.material?.itens.length || 0;
      const servicos = gruposRequisicao.servico?.itens.length || 0;
      requisicaoResumo.textContent = `Orçamento misto: ${materiais} material(is) e ${servicos} serviço(s). Selecione o tipo acima e gere uma requisição de cada vez.`;
    } else {
      requisicaoResumo.textContent = `${itensRequisicao.length} item(ns) encontrado(s) · Total bruto: ${total}`;
    }
    requisicaoDownload.disabled = false;
    requisicaoStatus.textContent = "Orçamento importado. Confira os itens antes de gerar.";
    requisicaoStatus.className = "status success";
  } catch (error) {
    requisicaoStatus.textContent = error.message;
    requisicaoStatus.className = "status error";
  }
});

document.getElementById("requisicao-tipo").addEventListener("change", (event) => {
  const grupo = gruposRequisicao[event.target.value];
  if (!grupo) {
    if (Object.keys(gruposRequisicao).length) {
      itensRequisicao = [];
      requisicaoItens.innerHTML = "";
      requisicaoResumo.textContent = `O orçamento não possui itens de ${event.target.value === "material" ? "material" : "serviço"}.`;
      requisicaoDownload.disabled = true;
    }
    return;
  }
  itensRequisicao = grupo.itens;
  desenharItensRequisicao();
  const total = grupo.total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  requisicaoResumo.textContent = `${itensRequisicao.length} item(ns) de ${event.target.value === "material" ? "material" : "serviço"} · Total bruto: ${total}`;
  requisicaoDownload.disabled = false;
});

requisicaoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!itensRequisicao.length) return;
  requisicaoDownload.disabled = true;
  requisicaoStatus.textContent = "Gerando requisição...";
  try {
    const dados = {
      fornecedor: document.getElementById("requisicao-fornecedor").value,
      endereco: document.getElementById("requisicao-endereco").value,
      cidade: document.getElementById("requisicao-cidade").value,
      destino: document.getElementById("requisicao-destino").value,
      fonte_recurso: document.getElementById("requisicao-fonte").value,
      identificacao: document.getElementById("requisicao-identificacao").value,
      desconto: document.getElementById("requisicao-desconto").value,
      itens: itensRequisicao,
      placa: metadadosRequisicao.placa,
      numero_orcamento: metadadosRequisicao.numero_orcamento,
      secretaria: currentSecretariat.value,
    };
    const response = await fetch("/api/requisicoes/download", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo: document.getElementById("requisicao-tipo").value, dados }),
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Não foi possível gerar a requisição.");
    }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    const disposicao = response.headers.get("Content-Disposition") || "";
    const nomeUtf8 = disposicao.match(/filename\*=UTF-8''([^;]+)/i);
    link.download = nomeUtf8 ? decodeURIComponent(nomeUtf8[1]) : "requisicao.xlsx";
    link.click();
    URL.revokeObjectURL(link.href);
    requisicaoStatus.textContent = "Requisição gerada com sucesso.";
    requisicaoStatus.className = "status success";
  } catch (error) {
    requisicaoStatus.textContent = error.message;
    requisicaoStatus.className = "status error";
  } finally {
    requisicaoDownload.disabled = false;
  }
});

const relatorioMes = document.getElementById("relatorio-mes");
const agoraRelatorio = new Date();
relatorioMes.value = `${agoraRelatorio.getFullYear()}-${String(agoraRelatorio.getMonth() + 1).padStart(2, "0")}`;
document.getElementById("relatorio-download").addEventListener("click", async () => {
  const status = document.getElementById("relatorio-status");
  if (!relatorioMes.value) {
    status.textContent = "Selecione o mês do relatório.";
    status.className = "status error";
    return;
  }
  const [ano, mes] = relatorioMes.value.split("-");
  const parametros = new URLSearchParams({ ano, mes });
  if (currentSecretariat.value) parametros.set("secretaria", currentSecretariat.value);
  status.textContent = "Gerando relatório...";
  try {
    const response = await fetch(`/api/requisicoes/relatorio?${parametros}`);
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Não foi possível gerar o relatório.");
    }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `RELATORIO VEICULOS ${ano}-${mes}.xlsx`;
    link.click();
    URL.revokeObjectURL(link.href);
    status.textContent = "Relatório gerado com sucesso.";
    status.className = "status success";
  } catch (error) {
    status.textContent = error.message;
    status.className = "status error";
  }
});

verificarAutenticacao();
