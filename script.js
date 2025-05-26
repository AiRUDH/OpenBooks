// Get important elements
const bookList = document.getElementById('bookList');
const hamburger = document.querySelector('.hamburger');
const navLinks = document.querySelector('.nav-links');

// Mobile menu toggle
hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navLinks.classList.toggle('active');
});

// Close mobile menu when clicking links
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
        hamburger.classList.remove('active');
        navLinks.classList.remove('active');
    });
});

// Load and display books
async function loadBooks() {
    try {
        bookList.innerHTML = '<div class="loading">Loading books...</div>';

        const response = await fetch('data.txt');
        const text = await response.text();
        const lines = text.split('\n').map(line => line.trim()).filter(line => line);

        const books = [];

        for (let i = 0; i < lines.length; i += 2) {
            if (i + 1 >= lines.length) {
                console.warn(`Unmatched title at line ${i + 1}`);
                break;
            }

            const title = lines[i];
            const url = lines[i + 1];

            let fileId = null;
            const viewMatch = url.match(/\/d\/([^/]+)\/view/);
            const idMatch = url.match(/id=([^&]+)/);

            if (viewMatch) fileId = viewMatch[1];
            else if (idMatch) fileId = idMatch[1];

            if (!fileId) continue;

            books.push({
                title: title,
                thumbnail: `https://drive.google.com/thumbnail?id=${fileId}`,
                readUrl: url,
                downloadUrl: `https://drive.google.com/uc?export=download&id=${fileId}`
            });
        }

        if (books.length === 0) {
            bookList.innerHTML = '<div class="no-results">No books found</div>';
            return;
        }

        bookList.innerHTML = books.map(book => `
            <div class="book-card">
                <div class="book-cover">
                    <img src="${book.thumbnail}" alt="Cover of ${book.title}" onerror="this.src='default-book.svg'">
                </div>
                <div class="book-info">
                    <h3>${book.title}</h3>
                    <div class="book-actions">
                        <a href="${book.readUrl}" target="_blank" class="read-btn">Read Online</a>
                        <a href="${book.downloadUrl}" target="_blank" class="download-btn">Download</a>
                    </div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error(error);
        bookList.innerHTML = '<div class="error-message">Could not load books. Please try again later.</div>';
    }
}

// Handle contact form
const contactForm = document.getElementById('suggestionForm');
if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('name').value.trim();
        const email = document.getElementById('email').value.trim();
        const message = document.getElementById('message').value.trim();

        if (!name || !email || !message) {
            document.getElementById('contactFormMessages').innerHTML =
                '<div class="error-message">Please fill in all fields</div>';
            return;
        }

        document.getElementById('contactFormMessages').innerHTML =
            '<div class="success-message">Message sent successfully!</div>';
        contactForm.reset();
    });
}

// Handle newsletter form
const newsletterForm = document.getElementById('newsletterForm');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = newsletterForm.querySelector('input[type="email"]').value.trim();

        if (!email) {
            document.getElementById('newsletterMessages').innerHTML =
                '<div class="error-message">Please enter your email</div>';
            return;
        }

        document.getElementById('newsletterMessages').innerHTML =
            '<div class="success-message">Thank you for subscribing!</div>';
        newsletterForm.reset();
    });
}

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(link.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Start loading books when page loads
document.addEventListener('DOMContentLoaded', loadBooks);
