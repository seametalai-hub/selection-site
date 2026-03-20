(function initApp() {
  const page = document.body.dataset.page;

  const params = new URLSearchParams(window.location.search);
  const currentCategory = params.get("category") || "";

  const state = {
    allProducts: [],
    filteredProducts: [],
    generatedAt: "",
  };

  const buildFallbackImage = () =>
    "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22 viewBox=%220 0 800 600%22%3E%3Crect width=%22800%22 height=%22600%22 fill=%22%2323333f%22/%3E%3Ctext x=%2260%22 y=%22300%22 font-size=%2240%22 fill=%22white%22 font-family=%22Segoe UI,Microsoft YaHei,sans-serif%22%3EImage unavailable%3C/text%3E%3C/svg%3E";

  const normalizeDateText = (value) => String(value || "").replace(/\s*上架$/, "").trim();

  const extractDateText = (value) => {
    const match = normalizeDateText(value).replace(/\//g, "-").match(/\d{4}-\d{2}-\d{2}/);
    return match ? match[0] : "";
  };

  const toDateValue = (value) => {
    const normalized = extractDateText(value);
    const date = normalized ? new Date(`${normalized}T00:00:00`) : new Date("");
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
  };

  const formatDate = (value) => {
    const text = normalizeDateText(value);
    const dateText = extractDateText(text);
    const date = dateText ? new Date(`${dateText}T00:00:00`) : new Date("");
    if (Number.isNaN(date.getTime())) {
      return text || "-";
    }
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
      date.getDate()
    ).padStart(2, "0")}`;
  };

  const toPrice = (value) => {
    const amount = Number(String(value || "").replace(/[¥￥,\s]/g, ""));
    return Number.isFinite(amount) ? amount : 0;
  };

  const formatPrice = (value) => {
    const amount = toPrice(value);
    return `¥${amount.toLocaleString("zh-CN")}`;
  };

  const toSales = (value) => {
    const text = String(value || "");
    const match = text.match(/(\d+(?:\.\d+)?)(万)?(\+)?/);
    if (!match) {
      return 0;
    }
    let base = Number(match[1]);
    if (match[2]) {
      base *= 10000;
    }
    return match[3] ? base + 0.5 : base;
  };

  const formatSales = (value) => String(value || "-");

  const matchesCategory = (product, selectedCategory) =>
    !selectedCategory || String(product.subCategory || "") === selectedCategory;

  const renderCategories = () => {
    const grid = document.getElementById("categoryGrid");
    if (!grid) {
      return;
    }

    grid.innerHTML = APP_DATA.categories
      .map(
        (category, index) => `
          <a class="category-card" href="./products.html?category=${encodeURIComponent(category.name)}">
            <span class="category-index">${String(index + 1).padStart(2, "0")}</span>
            <h3>${category.name}</h3>
            <p>${category.description}</p>
          </a>
        `
      )
      .join("");
  };

  const buildProductCard = (product) => `
    <article class="product-card">
      <div class="product-image-wrap">
        <img
          class="product-image"
          src="${product.image_url || buildFallbackImage()}"
          alt="${product.title || "未命名商品"}"
          loading="lazy"
          referrerpolicy="no-referrer"
          onerror="this.onerror=null;this.src='${buildFallbackImage()}';"
        />
      </div>
      <div class="product-body">
        <h3 class="product-title">${product.title || "未命名商品"}</h3>
        <div class="meta-row">
          <span class="price-tag">${formatPrice(product.price)}</span>
          <span class="sales-tag">销量 ${formatSales(product.sales_90d)}</span>
        </div>
        <dl class="product-meta">
          <div>
            <dt>发货地</dt>
            <dd>${product.origin || "-"}</dd>
          </div>
          <div>
            <dt>上架时间</dt>
            <dd>${formatDate(product.listed_time)}</dd>
          </div>
          <div class="supplier-meta">
            <dt>供应商</dt>
            <dd title="${product.supplier_name || "-"}">${product.supplier_name || "-"}</dd>
          </div>
        </dl>
        <a class="product-link" href="${product.product_url || "#"}" target="_blank" rel="noopener noreferrer">查看原链接</a>
      </div>
    </article>
  `;

  const fillOriginOptions = (products) => {
    const select = document.getElementById("originSelect");
    if (!select) {
      return;
    }

    const origins = [...new Set(products.map((item) => item.origin).filter(Boolean))].sort((a, b) =>
      a.localeCompare(b, "zh-CN")
    );

    select.innerHTML = ['<option value="">全部发货地</option>']
      .concat(origins.map((origin) => `<option value="${origin}">${origin}</option>`))
      .join("");
  };

  const sortProducts = (products, sortType) => {
    const list = [...products];
    if (sortType === "oldest") {
      list.sort((a, b) => {
        const dateGap = toDateValue(a.listed_time) - toDateValue(b.listed_time);
        if (dateGap !== 0) {
          return dateGap;
        }
        return toSales(b.sales_90d) - toSales(a.sales_90d);
      });
      return list;
    }
    if (sortType === "sales") {
      list.sort((a, b) => toSales(b.sales_90d) - toSales(a.sales_90d));
      return list;
    }
    if (sortType === "priceAsc") {
      list.sort((a, b) => toPrice(a.price) - toPrice(b.price));
      return list;
    }
    if (sortType === "priceDesc") {
      list.sort((a, b) => toPrice(b.price) - toPrice(a.price));
      return list;
    }
    list.sort((a, b) => {
      const dateGap = toDateValue(b.listed_time) - toDateValue(a.listed_time);
      if (dateGap !== 0) {
        return dateGap;
      }
      return toSales(b.sales_90d) - toSales(a.sales_90d);
    });
    return list;
  };

  const updateHeader = (count) => {
    const categoryTitle = document.getElementById("categoryTitle");
    const categoryDescription = document.getElementById("categoryDescription");
    const statCategory = document.getElementById("statCategory");
    const statCount = document.getElementById("statCount");
    const statDate = document.getElementById("statDate");
    const dataStatus = document.getElementById("dataStatus");

    if (categoryTitle) {
      categoryTitle.textContent = currentCategory || "商品列表";
    }
    if (categoryDescription) {
      categoryDescription.textContent = currentCategory
        ? `${currentCategory}类目下的商品，数据来自 products.json，可直接换电脑演示。`
        : "当前未指定类目。";
    }
    if (statCategory) {
      statCategory.textContent = currentCategory || "-";
    }
    if (statCount) {
      statCount.textContent = String(count);
    }
    if (statDate) {
      statDate.textContent = state.generatedAt || "-";
    }
    if (dataStatus) {
      dataStatus.textContent = `已读取 products.json，当前载入 ${state.allProducts.length} 条商品。`;
    }
  };

  const applyFilters = () => {
    const searchValue = (document.getElementById("searchInput")?.value || "").trim().toLowerCase();
    const originValue = document.getElementById("originSelect")?.value || "";
    const minPrice = document.getElementById("minPriceInput")?.value || "";
    const maxPrice = document.getElementById("maxPriceInput")?.value || "";
    const sortType = document.getElementById("sortSelect")?.value || "newest";
    const emptyState = document.getElementById("emptyState");
    const grid = document.getElementById("productGrid");

    let result = state.allProducts.filter((item) => matchesCategory(item, currentCategory));

    if (searchValue) {
      result = result.filter((item) =>
        [item.title, item.supplier_name, item.origin].some((value) => String(value || "").toLowerCase().includes(searchValue))
      );
    }

    if (originValue) {
      result = result.filter((item) => item.origin === originValue);
    }

    if (minPrice !== "") {
      result = result.filter((item) => toPrice(item.price) >= Number(minPrice));
    }

    if (maxPrice !== "") {
      result = result.filter((item) => toPrice(item.price) <= Number(maxPrice));
    }

    state.filteredProducts = sortProducts(result, sortType);
    updateHeader(state.filteredProducts.length);

    if (!grid || !emptyState) {
      return;
    }

    if (!state.filteredProducts.length) {
      emptyState.hidden = false;
      grid.innerHTML = "";
      return;
    }

    emptyState.hidden = true;
    grid.innerHTML = state.filteredProducts.map(buildProductCard).join("");
  };

  const bindFilters = () => {
    ["sortSelect", "searchInput", "originSelect", "minPriceInput", "maxPriceInput"].forEach((id) => {
      const element = document.getElementById(id);
      if (!element) {
        return;
      }
      element.addEventListener(id === "searchInput" ? "input" : "change", applyFilters);
      if (id === "minPriceInput" || id === "maxPriceInput") {
        element.addEventListener("input", applyFilters);
      }
    });
  };

  const loadProducts = async () => {
    const response = await fetch(APP_DATA.dataFile, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    state.generatedAt = payload.generated_at || "";
    state.allProducts = Array.isArray(payload.products) ? payload.products : [];
    fillOriginOptions(state.allProducts.filter((item) => matchesCategory(item, currentCategory)));
    applyFilters();
  };

  const initProductsPage = async () => {
    bindFilters();
    try {
      await loadProducts();
    } catch (error) {
      const dataStatus = document.getElementById("dataStatus");
      if (dataStatus) {
        dataStatus.textContent = `读取 products.json 失败：${error.message}`;
      }
    }
  };

  if (page === "categories") {
    renderCategories();
  }

  if (page === "products") {
    initProductsPage();
  }
})();


