$(document).ready(function () {
    // Function to format date as 'YYYY-MM-DD HH:MM:SS'
    function formatDate(date) {
        return date.toISOString().slice(0, 19).replace("T", " ");
    }

    // Calculate start time (30 days ago) and end time (now)
    const now = new Date();
    const startTime = new Date();
    startTime.setDate(startTime.getDate() - 30);

    const formattedStartTime = formatDate(startTime);
    const formattedEndTime = formatDate(now);

    // Fetch listings from the backend
    function fetchListings() {
        $.ajax({
            url: "https://backend.thriftlink.ink/getListings",
            type: "GET",
            data: {
                startTime: formattedStartTime,
                endTime: formattedEndTime
            },
            success: function (response) {
                displayListings(response);
            },
            error: function (xhr) {
                console.error("Failed to fetch listings:", xhr.responseText);
                $("#listingsContainer").html('<div class="text-danger">Failed to load listings.</div>');
            }
        });
    }

    // Function to display listings dynamically
    function displayListings(listings) {
        const container = $("#listingsContainer");
        container.empty(); // Clear previous listings

        if (listings.length === 0) {
            container.html('<div class="text-muted">No listings found.</div>');
            return;
        }

        listings.forEach(listing => {
            const photos = listing.photos.length > 0 ? `<img src="${listing.photos[0].photo_url}" class="img-fluid rounded" style="max-width: 100px;">` : '';
            const listingCard = `
                <div class="col-md-4">
                    <div class="card mb-3 p-2">
                        <div class="d-flex align-items-center">
                            ${photos}
                            <div class="ms-2">
                                <h6 class="mb-1">${listing.title}</h6>
                                <p class="mb-1 text-muted">$${listing.price}</p>
                                <small class="text-muted">By: ${listing.user.username}</small>
                            </div>
                        </div>
                    </div>
                </div>`;
            container.append(listingCard);
        });
    }

    // Call fetchListings on page load
    fetchListings();
});
