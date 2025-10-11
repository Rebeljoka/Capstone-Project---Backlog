(function () {
	const grid = document.getElementById("charts-grid");
	if (!grid) return;
	let loaded = false;

	function loadCSS(url) {
		return new Promise((resolve) => {
			const l = document.createElement("link");
			l.rel = "stylesheet";
			l.href = url;
			l.onload = resolve;
			l.onerror = resolve;
			document.head.appendChild(l);
		});
	}

	function loadJS(url) {
		return new Promise((resolve) => {
			const s = document.createElement("script");
			s.src = url;
			s.async = false;
			s.onload = resolve;
			s.onerror = resolve;
			document.body.appendChild(s);
		});
	}

	function runTemplate() {
		const tpl = document.getElementById("bokeh-script-template");
		if (!tpl) return;
		const frag = tpl.content?.cloneNode(true);
		if (!frag) return;
		const scripts = [...frag.querySelectorAll("script")];
		scripts.forEach((orig) => {
			const s = document.createElement("script");
			if (orig.textContent) s.text = orig.textContent;
			[...orig.attributes].forEach((attr) => s.setAttribute(attr.name, attr.value));
			document.body.appendChild(s);
		});
	}

	function loadBokeh() {
		if (loaded) return;
		loaded = true;
		console.log("Loading Bokeh assets now...");
		try {
			const dataEl = document.getElementById("bokeh-assets");
			const cfg = dataEl ? JSON.parse(dataEl.textContent || "{}") : { css: [], js: [] };
			Promise.all((cfg.css || []).map(loadCSS))
				.then(() => cfg.js.reduce((p, url) => p.then(() => loadJS(url)), Promise.resolve()))
				.then(runTemplate)
				.catch(() => {});
		} catch (e) {}
	}

	function isNearViewport(el, margin = 300) {
		const rect = el.getBoundingClientRect();
		return rect.top < window.innerHeight + margin && rect.bottom > -margin;
	}

	if (isNearViewport(grid)) {
		loadBokeh();
	} else if ("IntersectionObserver" in window) {
		const io = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						io.disconnect();
						loadBokeh();
					}
				});
			},
			{ rootMargin: "300px 0px", threshold: 0.01 }
		);
		io.observe(grid);
	} else {
		const onFirst = () => {
			window.removeEventListener("scroll", onFirst);
			loadBokeh();
		};
		window.addEventListener("scroll", onFirst, { once: true, passive: true });
		setTimeout(loadBokeh, 1500);
	}
})();
