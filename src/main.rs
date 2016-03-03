fn main() {
    let version = include_str!("version.txt");
    println!("Release testing v{}", version);
    std::process::exit(0);
}
