Jekyll::Hooks.register :site, :pre_render do |site, payload|
  if payload.jekyll.environment == "production"
    file = File.open("sitemap.txt", "w+")
    baseurl = Jekyll.configuration()["url"]
    site.pages.each do |page|
      if !((page.data.has_key?("tags") && page.data["tags"].include?("sitemap-exclude")) || page.ext != ".md")
        file.write "#{baseurl}#{page.url}\n"
      end
    end
    payload.site.posts.each do |post|
      if !(post.data.has_key?("tags") && post.data["tags"].include?("sitemap-exclude"))
        file.write "#{baseurl}#{post.url}\n"
      end
    end
    file.close()
  end
end