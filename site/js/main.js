document.addEventListener('DOMContentLoaded', () => {
  // Header scroll effect
  const header = document.getElementById('header');
  const updateHeader = () => {
    if (window.scrollY > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  };
  window.addEventListener('scroll', updateHeader, { passive: true });
  updateHeader();

  // Mobile menu
  const menuToggle = document.getElementById('menuToggle');
  const nav = document.getElementById('nav');

  menuToggle.addEventListener('click', () => {
    menuToggle.classList.toggle('active');
    nav.classList.toggle('open');
  });

  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      menuToggle.classList.remove('active');
      nav.classList.remove('open');
    });
  });

  // FAQ accordion
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    question.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      faqItems.forEach(i => i.classList.remove('open'));
      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });

  // Scroll reveal
  const revealElements = document.querySelectorAll(
    '.section-header, .problem-card, .feature-card, .step, .usecase-card, .pricing-card, .faq-item, .cta-card'
  );

  revealElements.forEach(el => el.classList.add('reveal'));

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        revealObserver.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });

  revealElements.forEach(el => revealObserver.observe(el));

  // Stagger for grids
  const grids = document.querySelectorAll('.problem-grid, .features-grid, .steps, .usecases-grid, .pricing-grid');
  grids.forEach(grid => {
    const children = grid.children;
    Array.from(children).forEach((child, index) => {
      child.style.transitionDelay = `${index * 80}ms`;
    });
  });

  // Contact form
  const contactForm = document.getElementById('contactForm');
  const formSuccess = document.getElementById('formSuccess');

  contactForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(contactForm);
    const data = Object.fromEntries(formData.entries());

    // In real integration, send data to backend or email service
    console.log('Form submitted:', data);

    contactForm.reset();
    formSuccess.classList.add('show');

    setTimeout(() => {
      formSuccess.classList.remove('show');
    }, 5000);
  });

  // Typing indicator animation loop
  const typing = document.getElementById('typing');
  if (typing) {
    setInterval(() => {
      typing.style.opacity = typing.style.opacity === '0' ? '1' : '0';
    }, 4000);
  }
});
