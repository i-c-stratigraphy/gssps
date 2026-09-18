# Read only the Mapbox setting; never evaluate .env as shell or Ruby code.
module MapboxToken
  def self.from_file(path)
    return nil unless File.file?(path)

    token = nil
    File.foreach(path) do |line|
      match = line.match(/^\s*(?:export\s+)?MAPBOX_ACCESS_TOKEN\s*=\s*(.*?)\s*$/)
      next unless match

      value = match[1]
      quoted = value.match(/\A(["'])(.*?)\1\s*(?:#.*)?\z/)
      token = quoted ? quoted[2] : value.sub(/\s+#.*\z/, "").strip
    end
    token
  end

  def self.load(source, environment = ENV)
    token = environment["MAPBOX_ACCESS_TOKEN"]
    if token.to_s.strip.empty? && environment["GITHUB_ACTIONS"] != "true"
      token = from_file(File.join(source, ".env"))
    end
    if token.to_s.strip.empty?
      raise Jekyll::Errors::FatalException,
            "Set MAPBOX_ACCESS_TOKEN in .env locally or in the GitHub Actions environment."
    end
    token
  end
end

Jekyll::Hooks.register :site, :after_init do |site|
  site.config["mapbox_access_token"] = MapboxToken.load(site.source)
end
