// Custom JavaScript for Aegis Guard Documentation

// Link the logo to the Aegis Guard repository.
document.addEventListener('DOMContentLoaded', function() {
  const logoLink = document.querySelector('.md-header__button.md-logo');
  if (logoLink) {
    logoLink.setAttribute('href', 'https://github.com/Raidensec/aegis-guard');
    logoLink.setAttribute('target', '_blank');
    logoLink.setAttribute('rel', 'noopener noreferrer');
  }
});
