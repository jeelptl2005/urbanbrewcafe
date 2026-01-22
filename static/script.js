// Wait for DOM to fully load
document.addEventListener('DOMContentLoaded', function() {
    
    // ===== Global Elements =====
    const menu = document.querySelector('.menu');
    const signupIn = document.querySelector('.signup-in');
    const menuToggle = document.querySelector('.menu-toggle');
    const header = document.querySelector('header');

    // ===== Mobile Menu Toggle - COMPLETELY FIXED =====
    if (menuToggle && menu && signupIn) {
        menuToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Menu toggle clicked'); // Debug line
            
            menu.classList.toggle('active');
            signupIn.classList.toggle('active');
            menuToggle.classList.toggle('active');
        });
    }

    // ===== Close menu when clicking a link =====
    const menuLinks = document.querySelectorAll('.menu a');
    menuLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (menu && signupIn && menuToggle) {
                menu.classList.remove('active');
                signupIn.classList.remove('active');
                menuToggle.classList.remove('active');
            }
        });
    });

    // ===== Close menu when clicking outside =====
    document.addEventListener('click', (e) => {
        if (
            menu && signupIn && menuToggle &&
            !menu.contains(e.target) &&
            !menuToggle.contains(e.target) &&
            !signupIn.contains(e.target)
        ) {
            menu.classList.remove('active');
            signupIn.classList.remove('active');
            menuToggle.classList.remove('active');
        }
    });

    // ===== Smooth scroll =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ===== Header shadow on scroll =====
    if (header) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                header.style.boxShadow = '0 4px 20px rgba(0,0,0,0.1)';
            } else {
                header.style.boxShadow = '0 2px 10px rgba(0,0,0,0.05)';
            }
        });
    }
    
});