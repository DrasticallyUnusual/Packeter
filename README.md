 Packeter is a cross-platform tool that downloads packages and dependencies via 14 package managers and generates install scripts for offline machines, without requiring you to reveal your hand to every registry in the chain. It provides a clean Tkinter GUI, auto-analyzes install scripts to resolve deep dependencies, and rewrites scripts to use local files instead of remote downloads.

The principle is simple: acquire what you need, offline, on your own terms. Download once, from a source you choose, on a connection you control. Then disconnect. The install script runs locally. No phone home. No telemetry. No dependency on services that do not serve you.

This is an initial step toward reclaiming the privacy that should never have been surrendered. Software freedom begins with the freedom to acquire software freely. Do no harm. Take no shit. Use responsibly. 

Supported Package Managers

Git
git clone - clones repositories with depth, branch, and tag support.

NPM
npm install - packs tarballs via npm pack without installing.

Pip
pip install - downloads wheels/sdists via pip download.

Cargo
cargo install - downloads crate source tarballs from crates.io.

Winget
winget install - downloads .msix/.exe/.msi via winget export/installer.

Chocolatey
choco install - downloads .nupkg packages for offline install.

Go
go install - downloads module source via go mod download.

Gem
gem install - fetches .gem files via gem fetch.

Docker
docker pull - pulls and saves images as .tar for offline loading.

Composer
composer require - downloads PHP packages via Composer.

APT
apt download - fetches .deb packages without installing.

DNF
dnf download - fetches .rpm packages without installing.

WSL
wsl --install - downloads WSL MSI and distro packages (.appxbundle).

Direct URL
https://... - downloads any file by URL, auto-detects install scripts.
