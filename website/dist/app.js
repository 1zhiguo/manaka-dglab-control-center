const form = document.querySelector('#feedbackForm');
form?.addEventListener('submit', (event) => {
  event.preventDefault();
  const title = document.querySelector('#feedbackTitle').value.trim();
  const body = document.querySelector('#feedbackBody').value.trim();
  if (!title || !body) return;
  const params = new URLSearchParams({ category: 'general', title, body });
  window.open(`https://github.com/1zhiguo/manaka-dglab-control-center/discussions/new?${params}`, '_blank', 'noopener,noreferrer');
});

const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) entry.target.classList.add('visible');
  }
}, { threshold: 0.12 });

document.querySelectorAll('.feature-card, .steps li, .feedback-form').forEach((element) => {
  element.classList.add('reveal');
  observer.observe(element);
});
