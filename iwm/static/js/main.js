const title = document.querySelector('.title');
const moreSmall = document.getElementById('moreSmall');
const smallDropdown = document.querySelector("#more-link-small .dropdown-menu");
const search = document.getElementById('search');
const seaBtn = document.getElementById('sea-btn');
const innerHeader = document.getElementById('i-h');
const searchBtn = document.getElementsByClassName('search-btn')[0];
const searchInput = document.getElementById("sea");
const clearBtn = document.getElementById("clear-btn");
const suggestionsContainer = document.getElementById('suggestions');


search.style.display = 'none';
let dropDown = false;

// Toggle the search bar on searchBtn click
searchBtn.addEventListener("click", (event) => {
    event.stopPropagation(); // Prevent the click from bubbling up
    if (search.style.display === 'flex') {
        // If already open, close it
        search.style.display = 'none';
        innerHeader.style.display = 'flex';
    } else {
        // Open search bar and hide header
        search.style.display = 'flex';
        innerHeader.style.display = 'none';
    }
});

// Toggle dropdown in the bottom nav
moreSmall.addEventListener("click", () => {
    dropDown = !dropDown;
    smallDropdown.style.display = dropDown ? 'block' : 'none';
});

// Extra: Close the search bar when clicking anywhere outside of it
document.addEventListener("click", (event) => {if (search.style.display === 'flex' && !search.contains(event.target)) {
    search.style.display = 'none';
    innerHeader.style.display = 'flex';
}});



searchInput.addEventListener("input", function() {
    clearBtn.style.display = this.value ? "block" : "none";
});

clearBtn.addEventListener("click", function() {
    searchInput.value = "";
    clearBtn.style.display = "none";
    searchInput.focus();
});

 

document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("sea");
    const suggestionsContainer = document.getElementById("suggestions");

    function debounce(func, delay) {
      let timeout;
      return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
      };
    }

    function fetchSuggestions() {
      const query = searchInput.value.trim();
      if (query.length < 2) {
        suggestionsContainer.innerHTML = "";
        return;
      }

      console.log("Fetching suggestions for:", query); // Debugging Log

      fetch(`/autocomplete/?q=${encodeURIComponent(query)}`)
        .then((response) => response.json())
        .then((data) => {
          console.log("Received suggestions:", data); // Debugging Log
          let suggestionsHtml = "";
          data.forEach((item) => {
            suggestionsHtml += `<div class="suggestion-item">
                                  <a href="${item.url}">${item.name}</a>
                                </div>`;
          });
          suggestionsContainer.innerHTML = suggestionsHtml;
        })
        .catch((error) => console.error("Error fetching suggestions:", error));
    }

    searchInput.addEventListener("input", debounce(fetchSuggestions, 300));
  });