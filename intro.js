

console.log("Intro script loaded");
document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM loaded, checking intro...");
    const forceIntro = new URLSearchParams(window.location.search).get("intro") === "1";
    
    // Smart animation logic: only play on first visit or explicit browser reload
    const navEntry = performance.getEntriesByType("navigation")[0];
    const isReload = navEntry && navEntry.type === "reload";
    const isSameOrigin = document.referrer && document.referrer.includes(window.location.host);
    
    let shouldPlay = forceIntro || isReload || !isSameOrigin;
    if (window.location.pathname && window.location.pathname.indexOf('overview') === -1 && window.location.pathname !== '/') {
        shouldPlay = false;
    }
    
    if (!shouldPlay) {
        console.log("Internal navigation detected, skipping intro");
        return;
    }

    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js";
    script.onload = () => {
        console.log("GSAP loaded, running intro");
        runIntro();
    };
    script.onerror = () => console.error("Failed to load GSAP from CDN");
    document.head.appendChild(script);
});

function runIntro() {
    document.body.style.overflow = "hidden";
    const isLight = document.documentElement.classList.contains("light-theme");
    // Explicit tint check
    console.log("Is light theme:", isLight);
    const cloudColorBase = isLight ? "120, 130, 125" : "100, 120, 140"; 
    
    const overlay = document.createElement("div");
    overlay.id = "intro-overlay";
    overlay.className = isLight ? "theme-light" : "theme-dark";
    
    const canvas = document.createElement("canvas");
    canvas.id = "intro-canvas";
    overlay.appendChild(canvas);
    
    const logoUrl = "https://lh3.googleusercontent.com/aida/AEtjO1XO6_tDByOL1sPBx-a585Vr97qtjvT1TPzq6q4qvx4rZpjcQmEw5FVe9AJpQ2IS1WsKCoKkZO0BwLFIO3wG454ByWYyS13dRob2kaqYCZ7Bly8zhWghZmgtwTsRJX7hlaFenacK2koZxoS_RtGeDEGAxZNnNlDWuP-G8QxsxAI1dFp9-HWC735X2TMAMK8tnKFYEGaDql25OqG0jbpOnrA5YCB8uneNHkBtHJCLYT4Glxj_tXoBYzkVsbgg";
    
    const logoHtml = `
        <div id="intro-logo-container">
            <img src="${logoUrl}" alt="Logo">
            <div id="intro-logo-text">
                <span id="intro-logo-title">UrbanAir Twin</span>
                <span id="intro-logo-subtitle">Metropolitan Intelligence</span>
            </div>
        </div>
    `;
    overlay.insertAdjacentHTML("beforeend", logoHtml);
    
    const skipBtn = document.createElement("button");
    skipBtn.id = "intro-skip";
    skipBtn.innerText = "Skip";
    overlay.appendChild(skipBtn);
    
    document.body.appendChild(overlay);
    
    const ctx = canvas.getContext("2d");
    let w, h;
    function resize() { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }
    window.addEventListener("resize", resize);
    resize();
    
    const clouds = [];
    const numClouds = 40;
    for (let i = 0; i < numClouds; i++) {
        clouds.push({
            x: w + 200 + Math.random() * 400, 
            y: Math.random() * h,
            r: 100 + Math.random() * 300,
            opacity: 0,
            targetX: w * Math.random(), 
            targetY: Math.random() * h,
            scale: 1
        });
    }
    
    let animationActive = true;
    function render() {
        if(!animationActive) return;
        ctx.clearRect(0, 0, w, h);
        
        ctx.fillStyle = isLight ? "rgba(240, 242, 240, 1)" : "rgba(18, 20, 19, 1)";
        ctx.fillRect(0,0,w,h);
        
        clouds.forEach(c => {
            const grad = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, c.r * c.scale);
            grad.addColorStop(0, `rgba(${cloudColorBase}, ${c.opacity})`);
            grad.addColorStop(0.5, `rgba(${cloudColorBase}, ${c.opacity * 0.5})`);
            grad.addColorStop(1, `rgba(${cloudColorBase}, 0)`);
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(c.x, c.y, c.r * c.scale, 0, Math.PI * 2);
            ctx.fill();
        });
        requestAnimationFrame(render);
    }
    render();
    
    const tl = gsap.timeline({ onComplete: cleanup });
    
    tl.to(clouds, {
        duration: 2,
        x: (i, c) => c.targetX,
        opacity: (i) => 0.4 + Math.random() * 0.5,
        ease: "power2.out",
        stagger: { amount: 0.5 }
    });
    
    const logoNode = document.getElementById("intro-logo-container");
    tl.to(logoNode, { duration: 0.8, opacity: 1, scale: 1, ease: "power2.out" }, 1.5);
    tl.to(logoNode, { duration: 0.4, opacity: 0, scale: 1.1 }, 3.5);
    
    tl.add(() => {
        console.log("Animating radial exit...");
        const cx = w/2, cy = h/2;
        gsap.to(clouds, {
            duration: 1.5,
            x: (i, c) => {
                const dx = c.x - cx;
                return cx + (dx || Math.random()) * 5;
            },
            y: (i, c) => {
                const dy = c.y - cy;
                return cy + (dy || Math.random()) * 5;
            },
            scale: 3,
            opacity: 0,
            ease: "power2.in",
            stagger: { amount: 0.2, from: "center" }
        });
        gsap.to(overlay, { duration: 1.5, opacity: 0, ease: "power2.inOut", delay: 0.5 });
    }, 3.8);
    
    skipBtn.addEventListener("click", () => { tl.kill(); cleanup(); });
    
    function cleanup() {
        console.log("Cleanup intro");
        animationActive = false;
        if(overlay.parentNode) overlay.remove();
        document.body.style.overflow = "";
    }
}
