document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm || "¿Confirmas esta operación?")) event.preventDefault();
    });
  });

  document.querySelectorAll(".config-ubigeo").forEach(async (control) => {
    const departamento = control.querySelector("[data-departamento]");
    const provincia = control.querySelector("[data-provincia]");
    const distrito = control.querySelector("[data-distrito]");
    const codigoInput = control.parentElement.querySelector("input[type=hidden]");
    const endpoint = control.dataset.ubigeoUrl;
    const opciones = (select, items, texto, valor = texto) => {
      select.replaceChildren(new Option(texto === "departamento" ? "Departamento" : texto === "provincia" ? "Provincia" : "Distrito", ""));
      items.forEach((item) => select.add(new Option(typeof item === "string" ? item : item[texto], typeof item === "string" ? item : item[valor])));
      select.disabled = items.length === 0;
    };
    const get = async (params) => {
      const url = new URL(endpoint, window.location.origin);
      Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
      const respuesta = await fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}});
      if (!respuesta.ok) throw new Error("No se pudo consultar el ubigeo");
      return respuesta.json();
    };
    try {
      const inicial = control.dataset.codigo ? (await get({nivel: "codigo", codigo: control.dataset.codigo})).resultado : null;
      opciones(departamento, (await get({nivel: "departamentos"})).resultados, "departamento");
      if (inicial) departamento.value = inicial.departamento;
      const cargarProvincias = async () => {
        opciones(provincia, departamento.value ? (await get({nivel: "provincias", departamento: departamento.value})).resultados : [], "provincia");
      };
      const cargarDistritos = async () => {
        opciones(distrito, departamento.value && provincia.value ? (await get({nivel: "distritos", departamento: departamento.value, provincia: provincia.value})).resultados : [], "distrito", "codigo");
      };
      departamento.addEventListener("change", async () => { provincia.value = ""; distrito.value = ""; codigoInput.value = ""; await cargarProvincias(); });
      provincia.addEventListener("change", async () => { distrito.value = ""; codigoInput.value = ""; await cargarDistritos(); });
      distrito.addEventListener("change", () => { codigoInput.value = distrito.value; });
      if (inicial) {
        await cargarProvincias(); provincia.value = inicial.provincia;
        await cargarDistritos(); distrito.value = inicial.codigo;
      }
    } catch (error) {
      control.insertAdjacentHTML("beforeend", '<small class="config-error-text">No se pudo cargar el ubigeo. Verifica el permiso y el catálogo.</small>');
    }
  });
});
